"""
Stockfish UCI wrapper using python-chess.

Provides a simple interface to run engine analysis on board positions.
One engine process is started on worker startup and reused for all analyses.
"""

import logging
from typing import Any

import chess
import chess.engine

from worker.config import settings

log = logging.getLogger(__name__)


class EngineWrapper:
    """
    Wraps a single Stockfish process for the lifetime of the worker.

    Usage:
        engine = EngineWrapper()
        engine.start()
        result = engine.analyse(board, depth=14, multipv=3)
        engine.stop()
    """

    def __init__(self, path: str = settings.stockfish_path):
        self.path = path
        self._engine: chess.engine.SimpleEngine | None = None
        self.name: str = "unknown"
        self.version: str | None = None

    def start(self) -> None:
        """Start the engine process and read its identification."""
        log.info("Starting Stockfish at %s", self.path)
        self._engine = chess.engine.SimpleEngine.popen_uci(self.path)

        # Read engine name and version from the UCI id response
        info = self._engine.id
        self.name = info.get("name", "unknown")
        self.version = info.get("author", "")
        log.info("Engine: %s (%s)", self.name, self.version)

    def stop(self) -> None:
        """Shut down the engine process."""
        if self._engine is not None:
            self._engine.quit()
            self._engine = None
            log.info("Engine stopped")

    def analyse(
        self,
        board: chess.Board,
        depth: int = settings.analysis_depth,
        multipv: int = settings.analysis_multipv,
    ) -> list[dict[str, Any]]:
        """
        Analyse a position and return multi-PV results.

        Returns a list of dicts, one per PV line, sorted by best first.
        Each dict contains:
            - 'score': PovScore (relative = from side-to-move's perspective)
            - 'pv': list of Move objects (principal variation)
            - 'depth': search depth reached

        If multipv=1, returns a list with one element.
        """
        if self._engine is None:
            raise RuntimeError("Engine not started")

        limit = chess.engine.Limit(depth=depth)
        infos = self._engine.analyse(
            board,
            limit,
            multipv=multipv,
        )

        # python-chess returns a list of info dicts when multipv > 1
        if isinstance(infos, dict):
            infos = [infos]

        return infos

    @property
    def is_running(self) -> bool:
        return self._engine is not None and self._engine.transport.is_active
