"""
Mistake type classifier using python-chess heuristics.

Each function inspects board positions and move data to determine the
mistake type. Returns the first matching type in priority order.

Types (matching plan section 10):
1. hanging_piece      — user piece is attacked and undefended after the move (caused by move)
2. missed_mate        — best move delivers checkmate
3. missed_fork        — best move attacks two or more valuable pieces
4. missed_pin         — best move creates an absolute pin
5. missed_skewer      — best move creates a skewer
6. missed_check       — best move delivers check
7. missed_capture     — best move captures material; user played non-capture
8. ignored_threat     — opponent created a threat on undefended piece; user didn't address it
9. back_rank          — king on back rank with mating pattern
10. conversion        — won position (>75%) collapses to <=55%
11. opening_error     — out of theory with >=10pt loss within first 12 moves
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


def _check_missed_pin(board_before: chess.Board, best_move: chess.Move, side: chess.Color) -> bool:
    """Check if the best move creates an absolute pin on an opponent piece."""
    try:
        board_after = board_before.copy()
        board_after.push(best_move)
        moved_piece = board_after.piece_at(best_move.to_square)
        if not moved_piece or moved_piece.piece_type not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
            return False

        opp_color = not side
        king_sq = board_after.king(opp_color)
        if king_sq is None:
            return False

        ray = chess.SquareSet.ray(best_move.to_square, king_sq)
        for sq in ray:
            target = board_after.piece_at(sq)
            if target and target.color == opp_color and target.piece_type != chess.KING:
                if board_after.is_pinned(opp_color, sq) and not board_before.is_pinned(opp_color, sq):
                    return True
    except Exception as exc:
        log.debug("Error checking missed pin: %s", exc)
    return False


def _check_missed_skewer(board_before: chess.Board, best_move: chess.Move, side: chess.Color) -> bool:
    """
    Check if best move skewers two enemy pieces along a ray.
    A skewer attacks a valuable enemy piece in front, which exposes a piece behind it.
    """
    try:
        board_after = board_before.copy()
        board_after.push(best_move)
        moved_piece = board_after.piece_at(best_move.to_square)
        if not moved_piece or moved_piece.piece_type not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
            return False

        opp_color = not side
        origin = best_move.to_square

        directions = []
        if moved_piece.piece_type in (chess.ROOK, chess.QUEEN):
            directions.extend([(-1, 0), (1, 0), (0, -1), (0, 1)])
        if moved_piece.piece_type in (chess.BISHOP, chess.QUEEN):
            directions.extend([(-1, -1), (-1, 1), (1, -1), (1, 1)])

        orig_file = chess.square_file(origin)
        orig_rank = chess.square_rank(origin)

        for df, dr in directions:
            pieces_hit: list[tuple[chess.Square, chess.Piece]] = []
            f, r = orig_file + df, orig_rank + dr
            while 0 <= f < 8 and 0 <= r < 8:
                sq = chess.square(f, r)
                p = board_after.piece_at(sq)
                if p:
                    pieces_hit.append((sq, p))
                    if len(pieces_hit) == 2:
                        break
                f += df
                r += dr

            if len(pieces_hit) == 2:
                (_, p1), (_, p2) = pieces_hit
                if p1.color == opp_color and p2.color == opp_color:
                    v1 = 1000 if p1.piece_type == chess.KING else PIECE_VALUES.get(p1.piece_type, 0)
                    v2 = PIECE_VALUES.get(p2.piece_type, 0)
                    if v1 > v2 and v2 >= PIECE_VALUES[chess.KNIGHT]:
                        return True
    except Exception as exc:
        log.debug("Error checking missed skewer: %s", exc)
    return False


def _check_hanging_piece(
    board_before: chess.Board,
    board_after_played: chess.Board,
    played_move: chess.Move,
    side: chess.Color,
) -> bool:
    """
    Check if user's move actively hung a piece (moved into attack, moved defender away,
    or opened a line attacking own piece).
    """
    # Check 1: User moved a piece directly to an attacked & undefended/underdefended square
    sq = played_move.to_square
    p = board_after_played.piece_at(sq)
    if p and p.color == side and p.piece_type != chess.KING:
        if _is_attacked_and_undefended(board_after_played, sq, side) or _attacked_by_lower_value(board_after_played, sq, side):
            return True

    # Check 2: Another user piece that was safe before the move became attacked/undefended
    for sq_i in chess.SQUARES:
        piece = board_after_played.piece_at(sq_i)
        if piece and piece.color == side and piece.piece_type != chess.KING:
            is_hung_now = (
                _is_attacked_and_undefended(board_after_played, sq_i, side) or
                _attacked_by_lower_value(board_after_played, sq_i, side)
            )
            if is_hung_now:
                was_hung_before = (
                    _is_attacked_and_undefended(board_before, sq_i, side) or
                    _attacked_by_lower_value(board_before, sq_i, side)
                )
                if not was_hung_before:
                    return True

    return False


def _check_ignored_threat(
    board_before: chess.Board,
    played_move: chess.Move,
    fen_after: str,
    side: chess.Color,
) -> bool:
    """
    Check if opponent created a threat against an undefended/underdefended user piece
    that the user failed to address.
    """
    try:
        threatened_sqs: list[chess.Square] = []
        for sq in chess.SQUARES:
            piece = board_before.piece_at(sq)
            if piece and piece.color == side and piece.piece_type != chess.KING:
                if _is_attacked_and_undefended(board_before, sq, side) or _attacked_by_lower_value(board_before, sq, side):
                    threatened_sqs.append(sq)

        if not threatened_sqs:
            return False

        # If user moved the threatened piece away
        if played_move.from_square in threatened_sqs:
            return False

        # If user captured an attacker of the threatened piece
        opp_color = not side
        for t_sq in threatened_sqs:
            if played_move.to_square in board_before.attackers(opp_color, t_sq):
                return False

        # Check if the piece remains threatened after user's move
        board_after_played = _board_from_fen(fen_after)
        for t_sq in threatened_sqs:
            p_after = board_after_played.piece_at(t_sq)
            if p_after and p_after.color == side:
                if (_is_attacked_and_undefended(board_after_played, t_sq, side) or
                        _attacked_by_lower_value(board_after_played, t_sq, side)):
                    return True
    except Exception as exc:
        log.debug("Error checking ignored threat: %s", exc)
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
    Classify a mistake and return (type, tags) in priority order according to plan.
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

        try:
            best_move = chess.Move.from_uci(best_uci)
            played_move = chess.Move.from_uci(played_uci)
        except Exception:
            return "other", tags

        board_after_played = _board_from_fen(fen_after)

        # 1. Hanging piece — user's move actively hung a piece
        if _check_hanging_piece(board_before, board_after_played, played_move, side):
            return "hanging_piece", tags

        # 2. Missed mate
        board_after_best = board_before.copy()
        board_after_best.push(best_move)
        if board_after_best.is_checkmate():
            return "missed_mate", tags

        # 3. Missed fork — best move attacks two or more valuable pieces
        attacked_valuable = 0
        for sq in chess.SQUARES:
            target = board_after_best.piece_at(sq)
            if target and target.color != side:
                if PIECE_VALUES.get(target.piece_type, 0) >= PIECE_VALUES[chess.KNIGHT]:
                    if board_after_best.is_attacked_by(side, sq):
                        attacked_valuable += 1
        if attacked_valuable >= 2:
            return "missed_fork", tags

        # 4. Missed pin — best move creates an absolute pin on opponent piece
        if _check_missed_pin(board_before, best_move, side):
            return "missed_pin", tags

        # 5. Missed skewer — best move creates a skewer on opponent pieces
        if _check_missed_skewer(board_before, best_move, side):
            return "missed_skewer", tags

        # 6. Missed check — best move gives check
        if board_before.gives_check(best_move):
            return "missed_check", tags

        # 7. Missed capture — best move is a capture, played move is not
        if board_before.is_capture(best_move) and not board_before.is_capture(played_move):
            return "missed_capture", tags

        # 8. Ignored threat — opponent threatened a piece and user failed to address it
        if _check_ignored_threat(board_before, played_move, fen_after, side):
            return "ignored_threat", tags

        # 9. Back rank — rook/queen delivers back rank mate pattern
        king_sq = board_after_best.king(not side)
        if king_sq is not None:
            king_rank = chess.square_rank(king_sq)
            if king_rank in (0, 7) and board_before.gives_check(best_move):
                best_piece = board_after_best.piece_at(best_move.to_square)
                if best_piece and best_piece.piece_type in (chess.ROOK, chess.QUEEN):
                    if chess.square_rank(best_move.to_square) == king_rank:
                        front_rank = 1 if king_rank == 0 else 6
                        king_file = chess.square_file(king_sq)
                        pawns_in_front = sum(
                            1 for f in [king_file - 1, king_file, king_file + 1]
                            if 0 <= f < 8
                            and (p := board_after_best.piece_at(chess.square(f, front_rank)))
                            and p.color != side
                        )
                        if pawns_in_front >= 2:
                            return "back_rank", tags

        # 10. Conversion — won position (>75%) collapses to <=55%
        if win_pct_before > CONVERSION_WIN_THRESHOLD and win_pct_after <= CONVERSION_COLLAPSE_THRESHOLD:
            return "conversion", tags

        # 11. Opening error — out of theory with >=10 win% loss within first 12 moves
        if ply <= OPENING_PLY_LIMIT and (win_pct_before - win_pct_after) >= 10.0:
            return "opening_error", tags

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
