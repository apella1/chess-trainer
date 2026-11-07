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


# ---------------------------------------------------------------------------
# Puzzle functions (Phase 3+)
# ---------------------------------------------------------------------------

def fetch_mistakes_with_evals(game_id: str) -> list[dict[str, Any]]:
    """
    Fetch all mistakes for a game with their move evals and move data.
    Joins mistakes, move_evals, and moves tables.
    """
    try:
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT m.id, m.kind, m.type, m.phase,
                       me.classification, me.win_pct_before, me.win_pct_loss,
                       me.best_uci, me.best_eval_cp, me.second_best_eval_cp,
                       mo.fen_before, mo.color, mo.ply, mo.san
                FROM mistakes m
                JOIN move_evals me ON m.move_eval_id = me.id
                JOIN moves mo ON me.move_id = mo.id
                WHERE m.game_id = %s
                ORDER BY mo.ply
                """,
                (game_id,),
            ).fetchall()
        return [dict(r) for r in rows]
    except psycopg.errors.UndefinedTable:
        log.debug("fetch_mistakes_with_evals: tables do not exist yet")
        return []


def insert_puzzle(
    user_id: str,
    source: str,
    source_mistake_id: str,
    fen: str,
    side_to_move: str,
    solution_uci: list[str],
    themes: list[str],
    difficulty_est: float,
) -> None:
    """Insert a new puzzle. solution_uci and themes are stored as JSONB."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO puzzles (user_id, source, source_mistake_id, fen, side_to_move, solution_uci, themes, difficulty_est)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
            """,
            (user_id, source, source_mistake_id, fen, side_to_move,
             json.dumps(solution_uci), json.dumps(themes), difficulty_est),
        )


def puzzle_exists_by_fen(user_id: str, fen: str) -> bool:
    """Check if a puzzle already exists for this user with the same FEN."""
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM puzzles WHERE (user_id = %s OR user_id IS NULL) AND fen = %s LIMIT 1",
                (user_id, fen),
            ).fetchone()
        return row is not None
    except psycopg.errors.UndefinedTable:
        return False


def enqueue_job(user_id: str, game_id: str, kind: str) -> None:
    """
    Enqueue a job from the worker side (e.g., generate_puzzles after analysis).
    Idempotent: checks if a job of this kind already exists for the game.
    """
    try:
        with get_conn() as conn:
            existing = conn.execute(
                "SELECT 1 FROM analysis_jobs WHERE game_id = %s AND kind = %s LIMIT 1",
                (game_id, kind),
            ).fetchone()
            if existing:
                return
            conn.execute(
                "INSERT INTO analysis_jobs (user_id, game_id, kind, status) VALUES (%s, %s, %s, 'pending')",
                (user_id, game_id, kind),
            )
    except psycopg.errors.UndefinedTable:
        log.debug("enqueue_job: analysis_jobs table does not exist yet")

# ---------------------------------------------------------------------------
# Game metadata and move listing (used by facts.py)
# ---------------------------------------------------------------------------

def get_game_metadata(game_id: str) -> dict[str, Any] | None:
    """Fetch game metadata for the facts package."""
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT result, user_color, user_rating, opp_rating, opp_username,
                   eco, opening_name, time_class, time_control
            FROM games WHERE id = %s
            """,
            (game_id,),
        ).fetchone()
    return dict(row) if row else None


def fetch_moves_with_evals(game_id: str) -> list[dict[str, Any]]:
    """Fetch all moves with their evals for a game, ordered by ply."""
    try:
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT mo.ply, mo.san, mo.color, mo.fen_before, mo.clock_ms_remaining,
                       me.classification, me.win_pct_before, me.win_pct_after, me.win_pct_loss,
                       me.best_uci, me.best_eval_cp
                FROM moves mo
                LEFT JOIN move_evals me ON me.move_id = mo.id
                WHERE mo.game_id = %s
                ORDER BY mo.ply
                """,
                (game_id,),
            ).fetchall()
        return [dict(r) for r in rows]
    except psycopg.errors.UndefinedTable:
        return []


# ---------------------------------------------------------------------------
# Review functions (Phase 4+)
# ---------------------------------------------------------------------------

def get_latest_analysis_run_id(game_id: str) -> str | None:
    """Get the most recent completed analysis run for a game."""
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id FROM analysis_runs
            WHERE game_id = %s AND status = 'done'
            ORDER BY created_at DESC LIMIT 1
            """,
            (game_id,),
        ).fetchone()
    return str(row["id"]) if row else None


def review_exists(game_id: str, model: str, prompt_version: str) -> bool:
    """Check if a review already exists for this (game, model, prompt_version)."""
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM game_reviews WHERE game_id=%s AND model=%s AND prompt_version=%s LIMIT 1",
                (game_id, model, prompt_version),
            ).fetchone()
        return row is not None
    except psycopg.errors.UndefinedTable:
        return False


def insert_review(
    game_id: str,
    run_id: str | None,
    model: str,
    prompt_version: str,
    facts_json: dict,
    review_json: dict,
    review_text: str,
    validation_status: str,
) -> None:
    """Insert a game review. Uses ON CONFLICT to replace if regenerating."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO game_reviews
                (game_id, run_id, model, prompt_version, facts_json, review_json, review_text, validation_status)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
            ON CONFLICT (game_id, model, prompt_version)
            DO UPDATE SET
                run_id = EXCLUDED.run_id,
                facts_json = EXCLUDED.facts_json,
                review_json = EXCLUDED.review_json,
                review_text = EXCLUDED.review_text,
                validation_status = EXCLUDED.validation_status,
                created_at = now()
            """,
            (game_id, run_id, model, prompt_version,
             json.dumps(facts_json), json.dumps(review_json), review_text, validation_status),
        )


def get_review(game_id: str) -> dict[str, Any] | None:
    """Fetch the most recent review for a game."""
    try:
        with get_conn() as conn:
            row = conn.execute(
                """
                SELECT id, game_id, model, prompt_version, facts_json, review_json,
                       review_text, validation_status, created_at
                FROM game_reviews
                WHERE game_id = %s
                ORDER BY created_at DESC LIMIT 1
                """,
                (game_id,),
            ).fetchone()
        return dict(row) if row else None
    except psycopg.errors.UndefinedTable:
        return None

# ---------------------------------------------------------------------------
# Reclassification (Phase 5+)
# ---------------------------------------------------------------------------

def fetch_mistakes_for_reclassify(game_id: str) -> list[dict[str, Any]]:
    """
    Fetch all mistakes for a game with the data needed for classify.py.
    Includes fen_before, fen_after, played uci, best_uci, win_pct values,
    ply, clock, and time_control.
    """
    try:
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT m.id as mistake_id,
                       mo.ply, mo.color, mo.uci as played_uci, mo.fen_before, mo.fen_after,
                       mo.clock_ms_remaining,
                       me.best_uci, me.win_pct_before, me.win_pct_after, me.win_pct_loss,
                       me.eval_before_cp,
                       g.time_control
                FROM mistakes m
                JOIN move_evals me ON m.move_eval_id = me.id
                JOIN moves mo ON me.move_id = mo.id
                JOIN games g ON m.game_id = g.id
                WHERE m.game_id = %s
                ORDER BY mo.ply
                """,
                (game_id,),
            ).fetchall()
        return [dict(r) for r in rows]
    except psycopg.errors.UndefinedTable:
        return []


def update_mistake_type(mistake_id: str, mistake_type: str, tags: list[str], phase: str) -> None:
    """Update the type, tags, and phase columns on a mistake row."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE mistakes SET type = %s, tags = %s, phase = %s WHERE id = %s",
            (mistake_type, tags, phase, mistake_id),
        )


def fetch_weakness_stats(user_id: str) -> list[dict[str, Any]]:
    """
    Aggregate weakness statistics: mistakes per 100 moves by type.
    Returns rows ordered by rate descending.
    """
    try:
        with get_conn() as conn:
            rows = conn.execute(
                """
                WITH user_moves AS (
                    SELECT count(*) as total_moves
                    FROM moves mo
                    JOIN games g ON mo.game_id = g.id
                    WHERE g.user_id = %s
                      AND g.analysis_status = 'done'
                      AND mo.color = (
                          CASE WHEN g.user_color = 'white' THEN 'white' ELSE 'black' END
                      )
                ),
                mistake_counts AS (
                    SELECT
                        COALESCE(m.type, 'other') as type,
                        m.phase,
                        count(*) as count
                    FROM mistakes m
                    WHERE m.user_id = %s
                    GROUP BY m.type, m.phase
                )
                SELECT
                    mc.type,
                    mc.phase,
                    mc.count,
                    ROUND(mc.count * 100.0 / NULLIF(um.total_moves, 0), 2) as rate_per_100
                FROM mistake_counts mc, user_moves um
                ORDER BY rate_per_100 DESC NULLS LAST
                """,
                (user_id, user_id),
            ).fetchall()
        return [dict(r) for r in rows]
    except psycopg.errors.UndefinedTable:
        return []


def get_user_id_by_username(username: str) -> str | None:
    """Get a user's ID by chess.com username."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE chesscom_username = %s",
            (username,),
        ).fetchone()
    return str(row["id"]) if row else None
