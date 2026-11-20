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

    def test_hanging_piece_underdefended(self):
        """Piece with more attackers than defenders is detected as hanging piece."""
        # White has Bishop on a1, Pawn on e3. Black has Knights on c6 and b5.
        # Both black knights attack d4. White plays Bd4, where d4 is defended once (by e3 pawn)
        # but attacked twice (by Nc6 and Nb5).
        board_before = chess.Board("4k3/8/2n5/1n6/8/4P3/7P/B5K1 w - - 0 1")
        fen_before = board_before.fen()
        board_after = board_before.copy()
        board_after.push_san("Bd4")
        fen_after = board_after.fen()

        m_type, _ = classify_mistake(
            fen_before=fen_before,
            fen_after=fen_after,
            played_uci="a1d4",
            best_uci="g1f2",
            win_pct_before=50.0,
            win_pct_after=25.0,
            ply=26,
            clock_ms=45000,
            time_control="600",
            eval_before_cp=0,
        )
        assert m_type == "hanging_piece"

    def test_missed_mate(self):
        """When best move delivers checkmate and played move does not."""
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

    def test_missed_fork_royal(self):
        """When best move forks the enemy King and Queen."""
        # White Knight on d5 can jump to c7: attacks King on e8 and Queen on a8
        board_before = chess.Board("q3k3/8/8/3N4/8/8/8/6K1 w - - 0 1")
        fen_before = board_before.fen()
        board_after = board_before.copy()
        board_after.push_san("Kf2")
        fen_after = board_after.fen()

        m_type, _ = classify_mistake(
            fen_before=fen_before,
            fen_after=fen_after,
            played_uci="g1f2",
            best_uci="d5c7",
            win_pct_before=70.0,
            win_pct_after=50.0,
            ply=20,
            clock_ms=40000,
            time_control="600",
            eval_before_cp=200,
        )
        assert m_type == "missed_fork"

    def test_missed_pin(self):
        """When best move creates an absolute pin on an opponent piece."""
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

    def test_classification_idempotent_and_deterministic(self):
        """
        Acceptance check: Classification results are deterministic and idempotent
        across re-runs.
        """
        board_before = chess.Board("4q2k/8/8/R7/8/8/7P/6K1 w - - 0 1")
        fen_before = board_before.fen()
        board_after = board_before.copy()
        board_after.push_san("h3")
        fen_after = board_after.fen()

        res1 = classify_mistake(
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
        res2 = classify_mistake(
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
        assert res1 == res2


class TestDeterminePhase:
    def test_opening_early(self):
        assert determine_phase_from_fen(chess.STARTING_FEN, ply=4) == "opening"

    def test_opening_with_undeveloped_minors(self):
        # Ply 10 but pieces still largely undeveloped on home squares
        assert determine_phase_from_fen(chess.STARTING_FEN, ply=10) == "opening"

    def test_middlegame(self):
        # Move past ply 24 with pieces on board
        assert determine_phase_from_fen(chess.STARTING_FEN, ply=26) == "middlegame"

    def test_endgame(self):
        # Queens gone and few pieces
        endgame_fen = "4k3/8/8/4p3/4P3/8/8/4K2R w K - 0 30"
        assert determine_phase_from_fen(endgame_fen, ply=30) == "endgame"
