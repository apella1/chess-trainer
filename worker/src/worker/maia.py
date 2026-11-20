"""
Optional Maia 1100 model comparison.

Maia is a neural network chess engine trained on Lichess games at specific rating bands
(such as ~1100) to predict the moves human players typically make.

Stockfish heuristics provide full coverage for all mistake classification, so Maia
remains an optional enhancement. If lc0 or weights are not installed, this module
gracefully falls back without errors.
"""

import logging
import shutil
from pathlib import Path
from typing import Any

import chess
import chess.engine

from worker.config import settings

log = logging.getLogger(__name__)


def is_maia_available() -> bool:
    """
    Check if lc0 binary and Maia weights are available and accessible.
    Returns False gracefully if either is missing.
    """
    if not settings.maia_weights_path:
        return False

    weights_file = Path(settings.maia_weights_path)
    if not weights_file.is_file():
        return False

    lc0_bin = shutil.which(settings.lc0_path) or (
        settings.lc0_path if Path(settings.lc0_path).is_file() else None
    )
    return lc0_bin is not None


def get_maia_prediction(board: chess.Board) -> str | None:
    """
    Query Maia 1100 for its top move prediction in the given position.
    Returns the UCI move string if available, or None on fallback/error.
    """
    if not is_maia_available():
        return None

    try:
        engine = chess.engine.SimpleEngine.popen_uci(
            [settings.lc0_path, f"--weights={settings.maia_weights_path}"]
        )
        try:
            result = engine.play(board, chess.engine.Limit(nodes=1))
            if result.move:
                return result.move.uci()
        finally:
            engine.quit()
    except Exception as exc:
        log.debug("Maia prediction unavailable (graceful fallback): %s", exc)
        return None

    return None


def compare_mistake_with_maia(
    board_before: chess.Board,
    played_uci: str,
) -> dict[str, Any] | None:
    """
    Compare the played mistake with Maia 1100's predicted move.
    If the user's blunder matches Maia's prediction, it is tagged as characteristic
    of the ~1100 rating band.
    Returns None if Maia is not available or if the move does not match.
    """
    predicted_uci = get_maia_prediction(board_before)
    if not predicted_uci:
        return None

    if predicted_uci == played_uci:
        return {
            "maia_move": predicted_uci,
            "is_characteristic": True,
            "rating_band": 1100,
            "note": "Mistake characteristic of ~1100 rating band (predicted by Maia)",
        }

    return None
