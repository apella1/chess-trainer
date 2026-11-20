"""
Unit tests for maia.py — optional Maia 1100 model comparison and graceful fallback.
"""

from unittest.mock import patch

import chess

from worker.maia import compare_mistake_with_maia, get_maia_prediction, is_maia_available


class TestMaiaComparison:
    def test_graceful_fallback_when_lc0_or_weights_missing(self):
        """
        Acceptance check: Maia comparison gracefully falls back without errors
        if lc0 or weights are not installed.
        """
        # When weights path is not configured or file doesn't exist
        with patch("worker.maia.settings") as mock_settings:
            mock_settings.maia_weights_path = "/nonexistent/path/to/maia-1100.pb.gz"
            mock_settings.lc0_path = "/nonexistent/lc0"

            assert not is_maia_available()
            assert get_maia_prediction(chess.Board()) is None
            assert compare_mistake_with_maia(chess.Board(), "e2e4") is None

    def test_graceful_fallback_on_engine_launch_failure(self):
        """If lc0 raises an OSError or EngineError during startup, catch gracefully."""
        with (
            patch("worker.maia.is_maia_available", return_value=True),
            patch("chess.engine.SimpleEngine.popen_uci", side_effect=OSError("binary format error")),
        ):
            pred = get_maia_prediction(chess.Board())
            assert pred is None

    def test_maia_matching_tag(self):
        """When Maia predicts the same move played by user, it returns characteristic mistake."""
        board = chess.Board()
        with (
            patch("worker.maia.is_maia_available", return_value=True),
            patch("worker.maia.get_maia_prediction", return_value="g1f3"),
        ):
            match = compare_mistake_with_maia(board, "g1f3")
            assert match is not None
            assert match["is_characteristic"] is True
            assert match["rating_band"] == 1100

            no_match = compare_mistake_with_maia(board, "e2e4")
            assert no_match is None
