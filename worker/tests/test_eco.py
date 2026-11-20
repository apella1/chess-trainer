"""
Unit tests for eco.py — ECO opening theory dataset and book move classification.
"""

import chess

from worker.eco import identify_opening_from_uci, is_book_move
from worker.winprob import classify_move


class TestEcoBook:
    def test_starting_moves_are_book(self):
        """Standard starting moves like e4, d4, Nf3, c4 are in book."""
        board = chess.Board()
        assert is_book_move(board, chess.Move.from_uci("e2e4"))
        assert is_book_move(board, chess.Move.from_uci("d2d4"))
        assert is_book_move(board, chess.Move.from_uci("c2c4"))
        assert is_book_move(board, chess.Move.from_uci("g1f3"))

    def test_non_book_move_is_not_book(self):
        """1. h4 or 1. a4 is not an established mainline book move."""
        board = chess.Board()
        assert not is_book_move(board, chess.Move.from_uci("h2h4"))
        assert not is_book_move(board, chess.Move.from_uci("a2a4"))

    def test_deep_book_line_italian_giuoco_piano(self):
        """Test Giuoco Piano moves beyond ply 10 are recognized as book moves."""
        board = chess.Board()
        # 1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4
        moves = ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "c2c3", "g8f6", "d2d4", "e5d4"]
        for uci in moves:
            move = chess.Move.from_uci(uci)
            assert is_book_move(board, move)
            board.push(move)

        # Ply 11: 6. cxd4 is in book!
        cxd4 = chess.Move.from_uci("c3d4")
        assert is_book_move(board, cxd4)

    def test_book_move_suppresses_blunder_classification(self):
        """Acceptance check: Opening moves conforming to ECO book theory are not classified as blunders."""
        board = chess.Board()
        # Advance 10 plies
        for uci in ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "c2c3", "g8f6", "d2d4", "e5d4"]:
            board.push(chess.Move.from_uci(uci))

        # Ply 11: 6. cxd4
        move = chess.Move.from_uci("c3d4")
        # Even with artificial bad eval loss, an ECO book move must be classified as "book"
        res = classify_move(
            eval_before_cp=100,
            eval_after_cp=-200,  # simulate engine drop
            mate_before=None,
            mate_after=None,
            played_is_best=False,
            ply=11,
            board_before=board,
            played_move=move,
        )
        assert res.classification == "book"

    def test_identify_opening_from_uci(self):
        """Recognize Italian Game Giuoco Piano from UCI sequence."""
        uci_str = "e2e4 e7e5 g1f3 b8c6 f1c4 f8c5 c2c3"
        identified = identify_opening_from_uci(uci_str)
        assert identified is not None
        eco, name = identified
        assert eco in ("C50", "C53", "C54")
        assert "Italian" in name or "Giuoco" in name
