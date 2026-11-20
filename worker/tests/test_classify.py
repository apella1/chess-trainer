"""
Unit tests for classify.py — mistake classification heuristics.

Tests every mistake type in isolation using python-chess positions.
Pure tests: no database, no engine, no network.
"""

import chess
from worker.classify import (
    classify_mistake,
    determine_phase_from_fen,
)


class TestClassifyMistake:
    def test_hanging_piece(self):
        """Moving a piece to an undefended, attacked square is a hanging_piece."""
        # White has Knight on b1, King on h1 (far away). Black has Rook on d8.
        # White plays Nd2 into the d-file, where Rook attacks it and no White piece defends it.
        board_before = chess.Board("3rk3/8/8/8/8/8/8/1N5K w - - 0 1")
        fen_before = board_before.fen()
        board_after = board_before.copy()
        board_after.push_san("Nd2")
        fen_after = board_after.fen()

        m_type, tags = classify_mistake(
            fen_before=fen_before,
            fen_after=fen_after,
            played_uci="b1d2",
            best_uci="b1c3",
            win_pct_before=45.0,
            win_pct_after=20.0,
            ply=20,
            clock_ms=60000,
            time_control="600",
            eval_before_cp=0,
        )
        assert m_type == "hanging_piece"

    def test_missed_mate(self):
        """When best move delivers checkmate and played move does not."""
        # Scholar's mate setup: White Queen on h5, Bishop on c4. Qxf7# is mate in 1.
        board_before = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4")
        fen_before = board_before.fen()
        board_after = board_before.copy()
        board_after.push_san("Nf3")
        fen_after = board_after.fen()

        m_type, tags = classify_mistake(
            fen_before=fen_before,
            fen_after=fen_after,
            played_uci="g1f3",
            best_uci="h5f7",
            win_pct_before=99.0,
            win_pct_after=55.0,
            ply=7,
            clock_ms=45000,
            time_control="600",
            eval_before_cp=1000,
        )
        assert m_type == "missed_mate"

    def test_missed_fork(self):
        """When best move attacks two or more valuable enemy pieces."""
        # White Knight on e5 jumps to c6: attacks Queen on b8 and Rook on e7.
        board_before = chess.Board("1q4k1/4r3/8/4N3/8/8/8/6K1 w - - 0 1")
        fen_before = board_before.fen()
        board_after = board_before.copy()
        board_after.push_san("Kf2")
        fen_after = board_after.fen()

        m_type, tags = classify_mistake(
            fen_before=fen_before,
            fen_after=fen_after,
            played_uci="g1f2",
            best_uci="e5c6",
            win_pct_before=60.0,
            win_pct_after=40.0,
            ply=30,
            clock_ms=40000,
            time_control="600",
            eval_before_cp=0,
        )
        assert m_type == "missed_fork"

    def test_missed_pin(self):
        """When best move creates an absolute pin on an opponent piece."""
        # Black King on h8, Black Queen on e8.
        # White Rook on a8 pins Queen to King on the 8th rank.
        board_before = chess.Board("4q2k/8/8/R7/8/8/7P/6K1 w - - 0 1")
        fen_before = board_before.fen()
        board_after = board_before.copy()
        board_after.push_san("h3")
        fen_after = board_after.fen()

        m_type, tags = classify_mistake(
            fen_before=fen_before,
            fen_after=fen_after,
            played_uci="h2h3",
            best_uci="a5a8",
            win_pct_before=55.0,
            win_pct_after=30.0,
            ply=30,
            clock_ms=40000,
            time_control="600",
            eval_before_cp=0,
        )
        assert m_type == "missed_pin"

    def test_missed_skewer(self):
        """When best move skewers a piece along a ray."""
        # Black King on e5, Black Queen on e2 (behind the King on the e-file).
        # White Rook on a8 plays Re8+ (skewers King and Queen).
        board_before = chess.Board("R7/8/8/4k3/8/8/4q3/6K1 w - - 0 1")
        fen_before = board_before.fen()
        board_after = board_before.copy()
        board_after.push_san("Kh1")
        fen_after = board_after.fen()

        m_type, tags = classify_mistake(
            fen_before=fen_before,
            fen_after=fen_after,
            played_uci="g1h1",
            best_uci="a8e8",
            win_pct_before=60.0,
            win_pct_after=40.0,
            ply=30,
            clock_ms=40000,
            time_control="600",
            eval_before_cp=0,
        )
        assert m_type == "missed_skewer"

    def test_missed_check(self):
        """When best move gives check without being a fork/pin/skewer."""
        # White Rook on a1 plays Rc1+ against Black King on c8.
        board_before = chess.Board("2k5/8/8/8/8/8/8/R3K3 w - - 0 1")
        fen_before = board_before.fen()
        board_after = board_before.copy()
        board_after.push_san("Kf2")
        fen_after = board_after.fen()

        m_type, tags = classify_mistake(
            fen_before=fen_before,
            fen_after=fen_after,
            played_uci="e1f2",
            best_uci="a1c1",
            win_pct_before=70.0,
            win_pct_after=60.0,
            ply=30,
            clock_ms=45000,
            time_control="600",
            eval_before_cp=200,
        )
        assert m_type == "missed_check"

    def test_missed_capture(self):
        """When best move is a capture and played move is not."""
        # White Rook on d1 is defended by King on e1.
        # Black Queen on d5 is undefended. Rxd5 captures the Queen.
        board_before = chess.Board("4k3/8/8/3q4/8/8/8/3RK3 w - - 0 1")
        fen_before = board_before.fen()
        board_after = board_before.copy()
        board_after.push_san("Ke2")
        fen_after = board_after.fen()

        m_type, tags = classify_mistake(
            fen_before=fen_before,
            fen_after=fen_after,
            played_uci="e1e2",
            best_uci="d1d5",
            win_pct_before=65.0,
            win_pct_after=35.0,
            ply=30,
            clock_ms=50000,
            time_control="600",
            eval_before_cp=0,
        )
        assert m_type == "missed_capture"

    def test_ignored_threat(self):
        """When opponent attacks user's piece and user fails to address it."""
        # Black Bishop on g4 attacks undefended White Queen on d1.
        # Best move is moving Queen to safety: d1c1 (non-capture).
        # White plays a3 on the queenside, ignoring the threat.
        board_before = chess.Board("4k3/8/8/8/6b1/8/P7/3QK3 w - - 0 1")
        fen_before = board_before.fen()
        board_after = board_before.copy()
        board_after.push_san("a3")
        fen_after = board_after.fen()

        m_type, tags = classify_mistake(
            fen_before=fen_before,
            fen_after=fen_after,
            played_uci="a2a3",
            best_uci="d1c1",
            win_pct_before=50.0,
            win_pct_after=30.0,
            ply=30,
            clock_ms=50000,
            time_control="600",
            eval_before_cp=0,
        )
        assert m_type == "ignored_threat"

    def test_conversion_collapse(self):
        """When win probability was >75% and collapses to <=55%."""
        board = chess.Board("4k3/8/8/8/8/8/4PPPP/4K3 w - - 0 35")
        fen = board.fen()
        m_type, _ = classify_mistake(
            fen_before=fen,
            fen_after=fen,
            played_uci="e2e3",
            best_uci="e2e4",
            win_pct_before=82.0,
            win_pct_after=52.0,
            ply=35,
            clock_ms=50000,
            time_control="600",
            eval_before_cp=250,
        )
        assert m_type == "conversion"

    def test_opening_error(self):
        """Non-tactical blunder within first 12 moves (24 plies) losing >=10% win chance."""
        board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        fen_before = board.fen()
        board_after = board.copy()
        board_after.push_san("h4")
        fen_after = board_after.fen()

        m_type, _ = classify_mistake(
            fen_before=fen_before,
            fen_after=fen_after,
            played_uci="h2h4",
            best_uci="e2e4",
            win_pct_before=50.0,
            win_pct_after=38.0,
            ply=2,
            clock_ms=60000,
            time_control="600",
            eval_before_cp=0,
        )
        assert m_type == "opening_error"

    def test_time_pressure_tag(self):
        """Clock < 30s triggers time_pressure tag."""
        board = chess.Board()
        fen = board.fen()
        _, tags = classify_mistake(
            fen_before=fen,
            fen_after=fen,
            played_uci="e2e4",
            best_uci="e2e4",
            win_pct_before=50.0,
            win_pct_after=50.0,
            ply=10,
            clock_ms=25000,  # 25 seconds
            time_control="600",
            eval_before_cp=0,
        )
        assert "time_pressure" in tags


class TestDeterminePhase:
    def test_opening(self):
        assert determine_phase_from_fen(chess.STARTING_FEN, ply=4) == "opening"

    def test_middlegame(self):
        # 16 plies with queens on board is middlegame
        assert determine_phase_from_fen(chess.STARTING_FEN, ply=16) == "middlegame"

    def test_endgame(self):
        # Queens gone and few pieces
        endgame_fen = "4k3/8/8/4p3/4P3/8/8/4K2R w K - 0 30"
        assert determine_phase_from_fen(endgame_fen, ply=30) == "endgame"
