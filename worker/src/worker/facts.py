"""
Facts package builder for LLM game reviews.

Assembles a structured JSON object from engine analysis data.
The LLM receives ONLY this package — it never computes chess facts itself.

Output schema:
{
  "game_id": "...",
  "result": "win|loss|draw",
  "user_color": "white|black",
  "user_rating": 1100,
  "opp_rating": 1095,
  "opp_username": "...",
  "opening": {"eco": "B01", "name": "Scandinavian Defense"},
  "time_class": "rapid",
  "time_control": "600",
  "total_moves": 54,
  "phase_mistake_counts": {"opening": 2, "middlegame": 5, "endgame": 1},
  "top_mistakes": [
    {
      "ply": 23, "san": "Nd4", "best_san": "Nf4",
      "best_uci": "f6f4", "fen_before": "...",
      "type": "hanging_piece", "win_pct_loss": 18.5,
      "clock_ms": 45000, "phase": "middlegame"
    }
  ]
}
"""

import logging
from typing import Any

from worker import db

log = logging.getLogger(__name__)

MAX_TOP_MISTAKES = 5


def build_facts(game_id: str) -> dict[str, Any] | None:
    """
    Build the structured facts package for a game.
    Returns None if the game has no analysis data yet.
    """
    game = db.get_game_metadata(game_id)
    if not game:
        log.warning("No game metadata for %s", game_id)
        return None

    mistakes = db.fetch_mistakes_with_evals(game_id)
    moves = db.fetch_moves_with_evals(game_id)

    if not moves:
        log.warning("No moves found for game %s — analysis may be incomplete", game_id)
        return None

    # Phase mistake counts
    phase_counts: dict[str, int] = {"opening": 0, "middlegame": 0, "endgame": 0}
    for m in mistakes:
        phase = m.get("phase") or "middlegame"
        phase_counts[phase] = phase_counts.get(phase, 0) + 1

    # Top mistakes sorted by severity (highest win_pct_loss first), capped at 5
    top_mistakes = sorted(
        mistakes,
        key=lambda m: float(m.get("win_pct_loss") or 0),
        reverse=True,
    )[:MAX_TOP_MISTAKES]

    # Format top mistakes for the LLM
    formatted_mistakes = []
    for m in top_mistakes:
        formatted_mistakes.append({
            "ply": m.get("ply"),
            "san": m.get("san"),
            "best_uci": m.get("best_uci"),
            "fen_before": m.get("fen_before"),
            "type": m.get("type") or "other",
            "phase": m.get("phase") or "middlegame",
            "win_pct_loss": round(float(m.get("win_pct_loss") or 0), 1),
            "clock_ms": m.get("clock_ms_remaining"),
        })

    return {
        "game_id": game_id,
        "result": game.get("result"),
        "user_color": game.get("user_color"),
        "user_rating": game.get("user_rating"),
        "opp_rating": game.get("opp_rating"),
        "opp_username": game.get("opp_username"),
        "opening": {
            "eco": game.get("eco"),
            "name": game.get("opening_name"),
        },
        "time_class": game.get("time_class"),
        "time_control": game.get("time_control"),
        "total_moves": len(moves),
        "phase_mistake_counts": phase_counts,
        "top_mistakes": formatted_mistakes,
    }
