"""
Mistake type classifier using python-chess heuristics.

Each function inspects board positions and move data to determine the
mistake type. Returns the first matching type in priority order.

Types (matching plan section 10):
1. hanging_piece      — user piece is attacked and undefended after the move
2. missed_mate        — best move delivers checkmate
3. missed_check       — best move delivers check
4. missed_capture     — best move captures material; user played non-capture
5. missed_fork        — best move attacks two or more valuable pieces
6. missed_pin         — best move creates an absolute pin
7. missed_skewer      — best move creates a skewer
8. ignored_threat     — opponent's last move created a threat; user didn't address it
9. back_rank          — king on back rank with mating pattern
10. conversion        — won position (>75%) collapses to ≤55%
11. opening_error     — out of theory with ≥10pt loss within first 12 moves
12. other             — fallback

Tags (orthogonal):
- time_pressure — clock < 30s or < 10% base time
"""

import logging
from typing import Any

import chess
import chess.pgn

log = logging.getLogger(__name__)

# Piece values for material swing detection
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

OPENING_PLY_LIMIT = 24  # first 12 moves per side

# Conversion thresholds
CONVERSION_WIN_THRESHOLD = 75.0
CONVERSION_COLLAPSE_THRESHOLD = 55.0

# Time pressure thresholds
TIME_PRESSURE_SECONDS = 30
TIME_PRESSURE_PCT = 0.10


def _board_from_fen(fen: str) -> chess.Board:
    return chess.Board(fen)


def _is_attacked_and_undefended(board: chess.Board, square: chess.Square, color: chess.Color) -> bool:
    """Check if a square containing a piece of `color` is attacked by opponent and not defended."""
    opponent = not color
    if not board.is_attacked_by(opponent, square):
        return False
    # Check if defended by own pieces
    if board.is_attacked_by(color, square):
        return False
    return True


def _attacked_by_lower_value(board: chess.Board, square: chess.Square, color: chess.Color) -> bool:
    """Check if piece on square is attacked by a lower-value opponent piece."""
    piece = board.piece_at(square)
    if piece is None:
        return False
    piece_value = PIECE_VALUES.get(piece.piece_type, 0)
    opponent = not color

    for attacker_sq in board.attackers(opponent, square):
        attacker = board.piece_at(attacker_sq)
        if attacker and PIECE_VALUES.get(attacker.piece_type, 0) < piece_value:
            return True
    return False


def classify_mistake(
    fen_before: str,
    fen_after: str,
    played_uci: str,
    best_uci: str,
    win_pct_before: float,
    win_pct_after: float,
    ply: int,
    clock_ms: int | None,
    time_control: str | None,
    eval_before_cp: int | None,
) -> tuple[str, list[str]]:
    """
    Classify a mistake and return (type, tags).

    All position analysis uses python-chess.
    """
    tags: list[str] = []

    # Time pressure tag
    if clock_ms is not None:
        clock_s = clock_ms / 1000
        if clock_s < TIME_PRESSURE_SECONDS:
            tags.append("time_pressure")
        elif time_control and "+" in time_control:
            try:
                base_s = int(time_control.split("+")[0])
                if base_s > 0 and (clock_s / base_s) < TIME_PRESSURE_PCT:
                    tags.append("time_pressure")
            except ValueError:
                pass

    try:
        board_before = _board_from_fen(fen_before)
        side = board_before.turn  # the side that made the mistake

        # 1. Conversion (check before board analysis — pure eval)
        if win_pct_before > CONVERSION_WIN_THRESHOLD and win_pct_after <= CONVERSION_COLLAPSE_THRESHOLD:
            return "conversion", tags

        # 2. Opening error
        if ply <= OPENING_PLY_LIMIT and eval_before_cp is not None:
            if abs(eval_before_cp) >= 10:
                return "opening_error", tags

        # Analyse best move on board_before
        try:
            best_move = chess.Move.from_uci(best_uci)
            played_move = chess.Move.from_uci(played_uci)
        except Exception:
            return "other", tags

        # 3. Missed mate
        board_after_best = board_before.copy()
        board_after_best.push(best_move)
        if board_after_best.is_checkmate():
            return "missed_mate", tags

        # 4. Missed check
        if board_before.gives_check(best_move):
            return "missed_check", tags

        # 5. Missed capture — best move is a capture, played move is not
        if board_before.is_capture(best_move) and not board_before.is_capture(played_move):
            return "missed_capture", tags

        # 6. Missed fork — best move attacks two or more valuable pieces
        board_after_best2 = board_before.copy()
        board_after_best2.push(best_move)
        piece_moved_sq = best_move.to_square
        attacked_valuable = 0
        for sq in chess.SQUARES:
            target = board_after_best2.piece_at(sq)
            if target and target.color != side:
                if PIECE_VALUES.get(target.piece_type, 0) >= PIECE_VALUES[chess.KNIGHT]:
                    if board_after_best2.is_attacked_by(side, sq):
                        attacked_valuable += 1
        if attacked_valuable >= 2:
            return "missed_fork", tags

        # 7. Hanging piece — after played move, user piece is undefended and attacked
        board_after_played = _board_from_fen(fen_after)
        for sq in chess.SQUARES:
            piece = board_after_played.piece_at(sq)
            if piece and piece.color == side:
                if piece.piece_type != chess.KING:
                    if (_is_attacked_and_undefended(board_after_played, sq, side) or
                            _attacked_by_lower_value(board_after_played, sq, side)):
                        return "hanging_piece", tags

        # 8. Back rank — rook/queen can deliver back rank mate
        king_sq = board_after_best2.king(not side)
        if king_sq is not None:
            king_rank = chess.square_rank(king_sq)
            if king_rank in (0, 7):
                # Check if rooks/queens on the back rank file threaten mate
                back_rank_attacked = True
                for escape_sq in [king_sq - 1, king_sq + 1]:
                    if 0 <= escape_sq < 64:
                        escape_piece = board_after_best2.piece_at(escape_sq)
                        if not escape_piece or escape_piece.color != (not side):
                            back_rank_attacked = False
                if back_rank_attacked:
                    return "back_rank", tags

    except Exception as exc:
        log.debug("Classification error: %s", exc)
        return "other", tags

    return "other", tags


def determine_phase_from_fen(fen: str, ply: int) -> str:
    """
    Determine game phase from position (piece count) rather than just ply.
    opening: < 12 plies
    endgame: queens gone and fewer than 12 minor/major pieces on board
    middlegame: everything else
    """
    if ply <= 12:
        return "opening"

    try:
        board = chess.Board(fen)
        # Count pieces (excluding pawns and kings)
        major_minor = sum(
            1 for sq in chess.SQUARES
            if (p := board.piece_at(sq)) is not None
            and p.piece_type not in (chess.PAWN, chess.KING)
        )
        queens = sum(
            1 for sq in chess.SQUARES
            if (p := board.piece_at(sq)) is not None
            and p.piece_type == chess.QUEEN
        )

        if queens == 0 and major_minor <= 6:
            return "endgame"
    except Exception:
        pass

    return "middlegame"
