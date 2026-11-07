"""
Reclassification pipeline.

Runs after analysis is complete and updates mistake type, phase, and tags
using the full classify.py heuristics. Called as part of the analyze_game
flow — no separate job kind needed.
"""

import logging

from worker import db
from worker.classify import classify_mistake, determine_phase_from_fen

log = logging.getLogger(__name__)


def reclassify_game(game_id: str) -> None:
    """
    Update type, phase, and tags for all mistakes in an analyzed game.
    Safe to call multiple times — always overwrites with the latest classification.
    """
    mistakes = db.fetch_mistakes_for_reclassify(game_id)
    if not mistakes:
        log.debug("No mistakes to reclassify for game %s", game_id)
        return

    log.info("Reclassifying %d mistake(s) for game %s", len(mistakes), game_id)

    for m in mistakes:
        try:
            mistake_type, tags = classify_mistake(
                fen_before=m["fen_before"],
                fen_after=m["fen_after"],
                played_uci=m["played_uci"],
                best_uci=m["best_uci"] or "",
                win_pct_before=float(m.get("win_pct_before") or 50),
                win_pct_after=float(m.get("win_pct_after") or 50),
                ply=m["ply"],
                clock_ms=m.get("clock_ms_remaining"),
                time_control=m.get("time_control"),
                eval_before_cp=m.get("eval_before_cp"),
            )

            phase = determine_phase_from_fen(m["fen_before"], m["ply"])

            db.update_mistake_type(
                str(m["mistake_id"]),
                mistake_type,
                tags,
                phase,
            )
        except Exception as exc:
            log.warning("Failed to reclassify mistake %s: %s", m.get("mistake_id"), exc)

    log.info("Reclassification done for game %s", game_id)
