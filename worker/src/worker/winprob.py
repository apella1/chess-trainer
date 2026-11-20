"""
Win probability conversion and move classification.

Converts centipawns evaluations to win probability using the Lichess formula:
    win% = 50 + 50 * (2 / (1 + exp(-0.00368208 * cp)) - 1)

Mate scores map to 100 (forced win) or 0 (forced loss).
All values are from the mover's perspective (positive = good for the side to move).

Classification thresholds (all tunable here):
    inaccuracy: 5 win% points
    mistake:    10 win% points
    blunder:    15 win% points
"""

import math
from typing import NamedTuple

import chess

from worker.eco import is_book_move

# --- Thresholds (tunable in one place) ---
INACCURACY_THRESHOLD = 5.0
MISTAKE_THRESHOLD = 10.0
BLUNDER_THRESHOLD = 15.0

# Skip classification for standard opening theory (first 10 plies unconditionally,
# or beyond if conforming to ECO theory)
OPENING_PLY_LIMIT = 10

# Coefficient for the Lichess win-probability formula
_CP_COEFF = 0.00368208


class MoveClassification(NamedTuple):
    classification: str  # book | best | good | inaccuracy | mistake | blunder
    win_pct_before: float
    win_pct_after: float
    win_pct_loss: float


def centipawns_to_win_pct(cp: float | None, mate: int | None = None) -> float:
    """
    Convert centipawns (mover's perspective) to win probability (0-100).
    Mate scores map to 100 (forced win) or 0 (forced loss).
    None cp returns 50.0 (unknown / equal).
    """
    if mate is not None:
        return 100.0 if mate > 0 else 0.0
    if cp is None:
        return 50.0
    return 50.0 + 50.0 * (2.0 / (1.0 + math.exp(-_CP_COEFF * cp)) - 1.0)


def classify_move(
    eval_before_cp: float | None,
    eval_after_cp: float | None,
    mate_before: int | None,
    mate_after: int | None,
    played_is_best: bool,
    ply: int,
    board_before: chess.Board | None = None,
    played_move: chess.Move | None = None,
) -> MoveClassification:
    """
    Classify a move based on win-probability loss and ECO opening book conformity.

    All eval values are from the mover's perspective (positive = good for the
    side that is about to move or just moved).

    Args:
        eval_before_cp: centipawns before the move (mover's perspective)
        eval_after_cp: centipawns after the move (mover's perspective, negated)
        mate_before: moves to mate before (None if no mate)
        mate_after: moves to mate after (None if no mate)
        played_is_best: whether the played move matches the engine's best move
        ply: 1-based ply number (odd = White, even = Black)
        board_before: optional chess.Board before the move for ECO book verification
        played_move: optional chess.Move played for ECO book verification

    Returns:
        MoveClassification with classification string and win% values.
    """
    win_pct_before = centipawns_to_win_pct(eval_before_cp, mate_before)
    win_pct_after = centipawns_to_win_pct(eval_after_cp, mate_after)
    win_pct_loss = win_pct_before - win_pct_after

    # Skip classification for opening theory moves:
    # 1. First 10 plies unconditionally
    # 2. Or if the move conforms to ECO book theory
    if ply <= OPENING_PLY_LIMIT or (
        board_before is not None
        and played_move is not None
        and is_book_move(board_before, played_move)
    ):
        return MoveClassification("book", win_pct_before, win_pct_after, win_pct_loss)

    if played_is_best:
        return MoveClassification("best", win_pct_before, win_pct_after, win_pct_loss)

    if win_pct_loss < INACCURACY_THRESHOLD:
        return MoveClassification("good", win_pct_before, win_pct_after, win_pct_loss)
    elif win_pct_loss < MISTAKE_THRESHOLD:
        return MoveClassification("inaccuracy", win_pct_before, win_pct_after, win_pct_loss)
    elif win_pct_loss < BLUNDER_THRESHOLD:
        return MoveClassification("mistake", win_pct_before, win_pct_after, win_pct_loss)
    else:
        return MoveClassification("blunder", win_pct_before, win_pct_after, win_pct_loss)


def is_mistake(classification: str) -> bool:
    """Check if a classification indicates a meaningful mistake."""
    return classification in ("inaccuracy", "mistake", "blunder")


def determine_phase(ply: int, fen: str) -> str:
    """
    Determine the game phase from piece count, material, and development.
    Delegates to classify.determine_phase_from_fen.
    """
    from worker.classify import determine_phase_from_fen

    return determine_phase_from_fen(fen, ply)
