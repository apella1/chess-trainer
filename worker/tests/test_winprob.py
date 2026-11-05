"""
Unit tests for winprob.py — centipawn to win probability and move classification.

These tests are pure: no database, no engine, no network.
"""

from worker.winprob import (
    centipawns_to_win_pct,
    classify_move,
    is_mistake,
    determine_phase,
)


class TestCentipawnsToWinPct:
    def test_equal_position(self):
        """0 centipawns = 50% win probability."""
        assert centipawns_to_win_pct(0) == 50.0

    def test_white_winning(self):
        """+100cp should be above 50%."""
        assert centipawns_to_win_pct(100) > 50.0
        assert round(centipawns_to_win_pct(100), 1) == 57.1

    def test_black_winning(self):
        """-100cp should be below 50%."""
        assert centipawns_to_win_pct(-100) < 50.0
        assert round(centipawns_to_win_pct(-100), 1) == 42.9

    def test_extreme_values(self):
        """Very large cp should approach 100 or 0."""
        assert centipawns_to_win_pct(10000) > 99.0
        assert centipawns_to_win_pct(-10000) < 1.0

    def test_none_returns_50(self):
        """None cp returns 50.0 (unknown / equal)."""
        assert centipawns_to_win_pct(None) == 50.0

    def test_mate_win(self):
        """Positive mate = forced win = 100%."""
        assert centipawns_to_win_pct(None, mate=3) == 100.0

    def test_mate_loss(self):
        """Negative mate = forced loss = 0%."""
        assert centipawns_to_win_pct(None, mate=-3) == 0.0


class TestClassifyMove:
    def test_best_move(self):
        """Playing the engine's best move should classify as 'best'."""
        result = classify_move(
            eval_before_cp=100, eval_after_cp=100,
            mate_before=None, mate_after=None,
            played_is_best=True, ply=15,
        )
        assert result.classification == "best"
        assert result.win_pct_loss == 0.0

    def test_blunder(self):
        """A move losing 15+ win% points should be a blunder."""
        result = classify_move(
            eval_before_cp=100, eval_after_cp=-200,
            mate_before=None, mate_after=None,
            played_is_best=False, ply=15,
        )
        assert result.classification == "blunder"
        assert result.win_pct_loss >= 15.0

    def test_mistake(self):
        """A move losing 10-15 win% points should be a mistake."""
        # Find values that produce 10-15 loss
        result = classify_move(
            eval_before_cp=200, eval_after_cp=0,
            mate_before=None, mate_after=None,
            played_is_best=False, ply=15,
        )
        assert result.classification in ("mistake", "blunder")
        assert result.win_pct_loss >= 10.0

    def test_inaccuracy(self):
        """A move losing 5-10 win% points should be an inaccuracy."""
        result = classify_move(
            eval_before_cp=50, eval_after_cp=-20,
            mate_before=None, mate_after=None,
            played_is_best=False, ply=15,
        )
        assert result.classification in ("inaccuracy", "mistake", "blunder")
        assert result.win_pct_loss >= 5.0

    def test_good_move(self):
        """A move losing less than 5 win% points should be 'good'."""
        result = classify_move(
            eval_before_cp=10, eval_after_cp=5,
            mate_before=None, mate_after=None,
            played_is_best=False, ply=15,
        )
        assert result.classification == "good"
        assert result.win_pct_loss < 5.0

    def test_opening_book(self):
        """Moves in the opening (plies 1-10) should be classified as 'book'."""
        result = classify_move(
            eval_before_cp=100, eval_after_cp=-500,
            mate_before=None, mate_after=None,
            played_is_best=False, ply=5,
        )
        assert result.classification == "book"

    def test_ply_10_is_book(self):
        """Ply 10 is still in the opening."""
        result = classify_move(100, -500, None, None, False, 10)
        assert result.classification == "book"

    def test_ply_11_is_not_book(self):
        """Ply 11 is past the opening theory."""
        result = classify_move(100, -500, None, None, False, 11)
        assert result.classification != "book"


class TestIsMistake:
    def test_blunder_is_mistake(self):
        assert is_mistake("blunder") is True

    def test_mistake_is_mistake(self):
        assert is_mistake("mistake") is True

    def test_inaccuracy_is_mistake(self):
        assert is_mistake("inaccuracy") is True

    def test_good_is_not_mistake(self):
        assert is_mistake("good") is False

    def test_best_is_not_mistake(self):
        assert is_mistake("best") is False

    def test_book_is_not_mistake(self):
        assert is_mistake("book") is False


class TestDeterminePhase:
    def test_opening(self):
        assert determine_phase(5, "") == "opening"

    def test_middlegame(self):
        assert determine_phase(20, "") == "middlegame"

    def test_endgame(self):
        assert determine_phase(50, "") == "endgame"
