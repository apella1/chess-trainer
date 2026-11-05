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
