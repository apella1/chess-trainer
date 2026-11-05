"""
Database layer for the worker.

ALL SQL lives in this module. No other module constructs or executes SQL queries.
This keeps analysis, puzzle, and review logic testable without a real database —
they call functions from this module which can be mocked in tests.
"""

import json
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from worker.config import settings

log = logging.getLogger(__name__)

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            settings.db_url,
            min_size=1,
            max_size=5,
            kwargs={"row_factory": dict_row},
        )
    return _pool


@contextmanager
def get_conn() -> Generator[psycopg.Connection, None, None]:
    """Yield a connection from the pool. Commits on success, rolls back on error."""
    pool = get_pool()
    with pool.connection() as conn:
        yield conn


def upsert_heartbeat(instance: str, details: dict[str, Any]) -> None:
    """
    Write (or update) the worker heartbeat row.
    Called every WORKER_POLL_SECONDS by the heartbeat thread.
    """
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO service_heartbeats (service, instance, last_seen, details)
            VALUES ('worker', %s, now(), %s)
            ON CONFLICT (service, instance)
            DO UPDATE SET last_seen = now(), details = EXCLUDED.details
            """,
            (instance, json.dumps(details)),
        )


def get_latest_heartbeat(service: str) -> dict[str, Any] | None:
    """Read the most recent heartbeat for a service (used in tests)."""
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT service, instance, last_seen, details
            FROM service_heartbeats
            WHERE service = %s
            ORDER BY last_seen DESC
            LIMIT 1
            """,
            (service,),
        ).fetchone()
    return dict(row) if row else None


def claim_job(instance_id: str) -> dict[str, Any] | None:
    """
    Claim the next pending job using SELECT ... FOR UPDATE SKIP LOCKED.
    Returns the job row or None if no job is available.

    Returns None (rather than raising) if the analysis_jobs table does not exist
    yet — this happens during early phases before the jobs migration has run.

    Priority: analyze_game and generate_puzzles before review_game, to avoid
    running Stockfish and Ollama simultaneously on resource-constrained machines.
    """
    try:
        with get_conn() as conn:
            row = conn.execute(
                """
                UPDATE analysis_jobs
                SET    status     = 'running',
                       locked_by  = %s,
                       locked_at  = now(),
                       attempts   = attempts + 1,
                       started_at = now()
                WHERE  id = (
                    SELECT id FROM analysis_jobs
                    WHERE  status = 'pending'
                      AND  attempts < max_attempts
                    ORDER BY
                        CASE kind
                            WHEN 'analyze_game'    THEN 1
                            WHEN 'generate_puzzles' THEN 2
                            WHEN 'review_game'     THEN 3
                            ELSE 4
                        END,
                        created_at
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING *
                """,
                (instance_id,),
            ).fetchone()
        return dict(row) if row else None
    except psycopg.errors.UndefinedTable:
        log.debug("claim_job skipped: analysis_jobs table does not exist yet")
        return None


def complete_job(job_id: str) -> None:
    """Mark a job as done."""
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE analysis_jobs
            SET status = 'done', finished_at = now()
            WHERE id = %s
            """,
            (job_id,),
        )


def fail_job(job_id: str, error: str, retry_after_seconds: int | None = None) -> None:
    """
    Mark a job as failed. If retry_after_seconds is given, reset to pending
    with a future created_at so the claim query skips it until the delay passes.
    """
    with get_conn() as conn:
        if retry_after_seconds is not None:
            conn.execute(
                """
                UPDATE analysis_jobs
                SET    status     = 'pending',
                       locked_by  = null,
                       locked_at  = null,
                       last_error = %s,
                       created_at = now() + (%s || ' seconds')::interval
                WHERE  id = %s
                """,
                (error, retry_after_seconds, job_id),
            )
        else:
            conn.execute(
                """
                UPDATE analysis_jobs
                SET    status      = 'failed',
                       finished_at = now(),
                       last_error  = %s
                WHERE  id = %s
                """,
                (error, job_id),
            )


def reset_stale_jobs(stale_after_minutes: int = 15) -> int:
    """
    Reaper: reset jobs that have been running for too long.
    Returns the number of jobs reset.

    Skips silently if the analysis_jobs table does not exist yet — this happens
    during early phases before the jobs migration has been applied. The reaper
    will become active once the table is created by Flyway.
    """
    try:
        with get_conn() as conn:
            result = conn.execute(
                """
                UPDATE analysis_jobs
                SET    status    = 'pending',
                       locked_by = null,
                       locked_at = null
                WHERE  status    = 'running'
                  AND  locked_at < now() - (%s || ' minutes')::interval
                """,
                (stale_after_minutes,),
            )
            count = result.rowcount
        if count:
            log.warning("Reaper reset %d stale job(s)", count)
        return count
    except psycopg.errors.UndefinedTable:
        log.debug("Reaper skipped: analysis_jobs table does not exist yet")
        return 0


# ---------------------------------------------------------------------------
# Analysis functions (Phase 2+)
# ---------------------------------------------------------------------------

def get_game_pgn(game_id: str) -> str | None:
    """Fetch the PGN text for a game."""
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT pgn FROM games WHERE id = %s",
                (game_id,),
            ).fetchone()
        return row["pgn"] if row else None
    except psycopg.errors.UndefinedTable:
        return None


def update_game_analysis_status(game_id: str, status: str) -> None:
    """Update the analysis_status column on the games table."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE games SET analysis_status = %s WHERE id = %s",
            (status, game_id),
        )


def get_game_user_id(game_id: str) -> str | None:
    """Fetch the user_id for a game."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT user_id FROM games WHERE id = %s",
            (game_id,),
        ).fetchone()
    return str(row["user_id"]) if row else None


def create_analysis_run(
    game_id: str,
    engine_name: str,
    engine_version: str,
    depth: int,
    multipv: int,
) -> str:
    """Create an analysis_runs row and return its ID."""
    with get_conn() as conn:
        row = conn.execute(
            """
            INSERT INTO analysis_runs (game_id, engine_name, engine_version, depth, multipv, status)
            VALUES (%s, %s, %s, %s, %s, 'running')
            RETURNING id
            """,
            (game_id, engine_name, engine_version, depth, multipv),
        ).fetchone()
    return str(row["id"])


def complete_analysis_run(run_id: str) -> None:
    """Mark an analysis run as done."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE analysis_runs SET status = 'done' WHERE id = %s",
            (run_id,),
        )


def insert_move(
    game_id: str,
    ply: int,
    color: str,
    san: str,
    uci: str,
    fen_before: str,
    fen_after: str,
    clock_ms: int | None,
    time_spent_ms: int | None,
) -> str:
    """Insert a move row and return its ID."""
    with get_conn() as conn:
        row = conn.execute(
            """
            INSERT INTO moves (game_id, ply, color, san, uci, fen_before, fen_after, clock_ms_remaining, time_spent_ms)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (game_id, ply, color, san, uci, fen_before, fen_after, clock_ms, time_spent_ms),
        ).fetchone()
    return str(row["id"])


def insert_move_eval(
    run_id: str,
    move_id: str,
    eval_before_cp: int | None,
    eval_after_cp: int | None,
    mate_before: int | None,
    mate_after: int | None,
    best_uci: str | None,
    best_eval_cp: int | None,
    second_best_eval_cp: int | None,
    pv_json: dict | None,
    win_pct_before: float | None,
    win_pct_after: float | None,
    win_pct_loss: float | None,
    classification: str | None,
) -> None:
    """Insert a move evaluation row."""
    import json
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO move_evals (
                run_id, move_id,
                eval_before_cp, eval_after_cp, mate_before, mate_after,
                best_uci, best_eval_cp, second_best_eval_cp,
                pv_json, win_pct_before, win_pct_after, win_pct_loss, classification
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (run_id, move_id, eval_before_cp, eval_after_cp, mate_before, mate_after,
             best_uci, best_eval_cp, second_best_eval_cp,
             json.dumps(pv_json) if pv_json else None,
             win_pct_before, win_pct_after, win_pct_loss, classification),
        )


def insert_mistake(
    game_id: str,
    user_id: str,
    move_eval_id: str,
    kind: str,
    mistake_type: str | None,
    tags: list[str] | None,
    phase: str | None,
    severity: float | None,
    material_swing_cp: int | None,
) -> None:
    """Insert a mistake row."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO mistakes (game_id, user_id, move_eval_id, kind, type, tags, phase, severity, material_swing_cp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (game_id, user_id, move_eval_id, kind, mistake_type, tags, phase, severity, material_swing_cp),
        )


def get_move_eval_id(run_id: str, move_id: str) -> str | None:
    """Get the move_eval ID for a given run and move."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM move_evals WHERE run_id = %s AND move_id = %s",
            (run_id, move_id),
        ).fetchone()
    return str(row["id"]) if row else None


def clear_game_analysis(game_id: str) -> None:
    """
    Delete all analysis data for a game (mistakes, move_evals, moves, runs).
    Called before re-analysis to ensure no duplicate rows on restart.
    Safe to call even if no analysis data exists yet.
    """
    try:
        with get_conn() as conn:
            conn.execute("DELETE FROM mistakes WHERE game_id = %s", (game_id,))
            conn.execute(
                "DELETE FROM move_evals WHERE run_id IN (SELECT id FROM analysis_runs WHERE game_id = %s)",
                (game_id,),
            )
            conn.execute("DELETE FROM moves WHERE game_id = %s", (game_id,))
            conn.execute("DELETE FROM analysis_runs WHERE game_id = %s", (game_id,))
    except psycopg.errors.UndefinedTable:
        log.debug("clear_game_analysis skipped: tables do not exist yet")
