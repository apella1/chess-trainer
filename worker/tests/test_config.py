"""
Phase 0 smoke tests for the worker.

Tests that do not require a real database or Stockfish.
"""

import os
import pytest


def test_settings_load_from_env(monkeypatch):
    """Settings load correctly from environment variables."""
    monkeypatch.setenv("DB_URL", "postgresql://user:pw@localhost:5432/test")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.1:8b")

    # Re-import to pick up the monkeypatched env
    import importlib
    import worker.config as config_module

    importlib.reload(config_module)
    s = config_module.Settings()

    assert s.db_url == "postgresql://user:pw@localhost:5432/test"
    assert s.ollama_model == "llama3.1:8b"
    assert s.analysis_depth == 14
    assert s.worker_poll_seconds == 5
