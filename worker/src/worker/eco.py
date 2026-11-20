"""
ECO opening theory dataset and book move classifier.

Integrates opening variations to:
1. Identify ECO codes and opening names from move sequences and positions.
2. Detect whether a position or move conforms to book theory.
3. Suppress false tactical blunder flags for recognized book moves.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import chess

log = logging.getLogger(__name__)

DATA_PATH = Path(__file__).parent / "data" / "openings.json"

_BOOK_MOVES: dict[str, set[str]] = {}
_BOOK_OPENINGS: dict[str, tuple[str, str]] = {}
_INITIALIZED = False


def _fen_key(board: chess.Board) -> str:
    """Normalized FEN key ignoring halfmove clock and fullmove number."""
    return " ".join(board.fen().split()[:4])


def _load_openings() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    if not DATA_PATH.exists():
        log.warning("ECO openings dataset not found at %s", DATA_PATH)
        _INITIALIZED = True
        return

    try:
        with open(DATA_PATH, encoding="utf-8") as f:
            openings: list[dict[str, Any]] = json.load(f)

        for op in openings:
            eco = op.get("eco", "")
            name = op.get("name", "")
            moves_uci = op.get("moves", [])

            board = chess.Board()
            for uci in moves_uci:
                key = _fen_key(board)
                if key not in _BOOK_MOVES:
                    _BOOK_MOVES[key] = set()
                _BOOK_MOVES[key].add(uci)

                try:
                    move = chess.Move.from_uci(uci)
                    if move in board.legal_moves:
                        board.push(move)
                        # Record the latest (most specific) opening name for this position
                        next_key = _fen_key(board)
                        _BOOK_OPENINGS[next_key] = (eco, name)
                except Exception as exc:
                    log.debug("Error pushing move %s for opening %s: %s", uci, name, exc)
                    break

        _INITIALIZED = True
        log.info("Loaded %d ECO openings, %d book positions", len(openings), len(_BOOK_MOVES))
    except Exception as exc:
        log.warning("Failed to load ECO dataset: %s", exc)
        _INITIALIZED = True


def is_book_move(board_before: chess.Board, move: chess.Move) -> bool:
    """
    Check if `move` is an established ECO book move in `board_before`.
    """
    if not _INITIALIZED:
        _load_openings()

    key = _fen_key(board_before)
    book_moves = _BOOK_MOVES.get(key)
    if not book_moves:
        return False
    return move.uci() in book_moves


def is_book_position(board: chess.Board) -> bool:
    """
    Check if the position in `board` is a known book position.
    """
    if not _INITIALIZED:
        _load_openings()

    key = _fen_key(board)
    return key in _BOOK_MOVES or key in _BOOK_OPENINGS


def lookup_position(board: chess.Board) -> tuple[str, str] | None:
    """
    Look up the ECO code and opening name for the current position.
    """
    if not _INITIALIZED:
        _load_openings()

    key = _fen_key(board)
    return _BOOK_OPENINGS.get(key)


@lru_cache(maxsize=128)
def identify_opening_from_uci(moves_uci_str: str) -> tuple[str, str] | None:
    """
    Identify opening from a space-separated string of UCI moves.
    Returns (eco, name) for the longest recognized prefix.
    """
    if not _INITIALIZED:
        _load_openings()

    moves = moves_uci_str.strip().split()
    board = chess.Board()
    last_known: tuple[str, str] | None = None

    for uci in moves:
        try:
            move = chess.Move.from_uci(uci)
            if move not in board.legal_moves:
                break
            board.push(move)
            pos_info = lookup_position(board)
            if pos_info:
                last_known = pos_info
        except Exception:
            break

    return last_known
