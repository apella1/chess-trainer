"""
Puzzle generation from analyzed game mistakes.

Quality filters (from the plan):
1. Best move beats second-best by at least 15 win-percentage points (unique solution)
2. Skip positions already decided: win_pct_before outside 20-90 range
3. Default solution length is 1-3 user moves (we use 1 for now)
4. Include missed opportunities (opponent blundered, user didn't punish)
5. Deduplicate by FEN
6. Store the full engine line so the UI can show the refutation
"""

import logging
from typing import Any

from worker import db, winprob

log = logging.getLogger(__name__)

# --- Quality filter thresholds ---
UNIQUENESS_THRESHOLD = 15.0  # win% points — best must beat second-best by this
WIN_PCT_MIN = 20.0           # skip positions where mover is already winning/losing
WIN_PCT_MAX = 90.0
BLUNDER_THRESHOLD = 15.0     # for difficulty estimation


def generate_puzzles(job: dict[str, Any]) -> None:
    """
    Generate puzzles from the mistakes in an analyzed game.

    Called by the main loop when a generate_puzzles job is claimed.
    Reads mistakes + move_evals from the database, applies quality filters,
    and inserts puzzle rows.

    The job payload contains:
    - game_id: UUID of the analyzed game
    """
    game_id = str(job["game_id"])
    user_id = db.get_game_user_id(game_id)
    if user_id is None:
        raise ValueError(f"Game {game_id} not found")

    # Fetch all mistakes with their evals and move data
    mistakes = db.fetch_mistakes_with_evals(game_id)
    if not mistakes:
        log.info("No mistakes found for game %s, skipping puzzle generation", game_id)
        return

    log.info("Generating puzzles from %d mistakes in game %s", len(mistakes), game_id)

    created = 0
    skipped = 0

    for mistake in mistakes:
        # Quality filter 1: win_pct_before must be in [20, 90] (not decided)
        win_pct_before = mistake.get("win_pct_before")
        if win_pct_before is None:
            skipped += 1
            continue
        if win_pct_before < WIN_PCT_MIN or win_pct_before > WIN_PCT_MAX:
            skipped += 1
            continue

        # Quality filter 2: best move must beat second-best by 15+ win% points
        best_eval_cp = mistake.get("best_eval_cp")
        second_best_eval_cp = mistake.get("second_best_eval_cp")
        if best_eval_cp is None or second_best_eval_cp is None:
            # Can't determine uniqueness without multi-PV — skip
            skipped += 1
            continue

        best_win_pct = winprob.centipawns_to_win_pct(best_eval_cp)
        second_win_pct = winprob.centipawns_to_win_pct(second_best_eval_cp)
        uniqueness = best_win_pct - second_win_pct
        if uniqueness < UNIQUENESS_THRESHOLD:
            skipped += 1
            continue

        # Quality filter 3: deduplicate by FEN
        fen_before = mistake.get("fen_before")
        if fen_before is None:
            skipped += 1
            continue
        if db.puzzle_exists_by_fen(user_id, fen_before):
            skipped += 1
            continue

        # Build the puzzle
        best_uci = mistake.get("best_uci")
        if not best_uci:
            skipped += 1
            continue

        # Solution: the best move (1-move solution for now)
        solution_uci = [best_uci]

        # Themes: use the mistake type if available, otherwise classification
        mistake_type = mistake.get("type") or "other"
        classification = mistake.get("classification") or "mistake"
        themes = [mistake_type, classification]

        # Side to move: the color of the player who made the mistake
        color = mistake.get("color") or "white"

        # Difficulty estimate: based on win_pct_loss (higher = harder to spot)
        win_pct_loss = mistake.get("win_pct_loss") or 0.0
        difficulty_est = min(win_pct_loss / BLUNDER_THRESHOLD, 1.0)

        # Insert the puzzle
        db.insert_puzzle(
            user_id=user_id,
            source="own_game",
            source_mistake_id=str(mistake["id"]),
            fen=fen_before,
            side_to_move=color,
            solution_uci=solution_uci,
            themes=themes,
            difficulty_est=difficulty_est,
        )
        created += 1

    log.info("Puzzle generation for game %s: created=%d, skipped=%d", game_id, created, skipped)
