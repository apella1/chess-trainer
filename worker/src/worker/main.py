"""
Worker entrypoint.

Responsibilities:
1. Run the reaper on startup (reset stale running jobs).
2. Start the heartbeat thread (writes service_heartbeats every WORKER_POLL_SECONDS).
3. Run the main claim loop indefinitely.

Job handlers are dispatched by job kind. In Phase 0, no job kinds are handled yet —
the worker loops, writes heartbeats, checks Ollama, and sleeps.
"""

import logging
import os
import socket
import threading
import time
from typing import Any

import httpx

from worker.config import settings
from worker.db import claim_job, complete_job, fail_job, reset_stale_jobs, upsert_heartbeat
from worker.engine import EngineWrapper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger(__name__)


def get_instance_id() -> str:
    """Return a stable identifier for this worker process."""
    if settings.worker_instance_id:
        return settings.worker_instance_id
    return socket.gethostname()


def check_ollama_reachable(url: str) -> bool:
    """Check whether Ollama is reachable by hitting its version endpoint."""
    try:
        response = httpx.get(f"{url}/api/version", timeout=3.0)
        return response.status_code == 200
    except Exception:
        return False


def check_ollama_model_ready(url: str, model: str) -> bool:
    """
    Check whether the configured model is fully downloaded and available.

    Hits GET /api/tags and looks for the model name in the response.
    A model that is still downloading will not appear in this list.
    Returns False if Ollama is unreachable.
    """
    try:
        response = httpx.get(f"{url}/api/tags", timeout=5.0)
        if response.status_code != 200:
            return False
        data = response.json()
        available = [m.get("name", "") for m in data.get("models", [])]
        # Ollama model names may or may not include a tag (e.g. "qwen3:8b" or "qwen3")
        # Match if the configured name is a prefix of any available name
        return any(name == model or name.startswith(model.split(":")[0] + ":") and model in name
                   for name in available)
    except Exception:
        return False


def heartbeat_loop(instance_id: str, stop_event: threading.Event) -> None:
    """
    Background thread: write a heartbeat row every WORKER_POLL_SECONDS.

    Reports three Ollama-related facts in the details payload:
    - ollamaReachable: Ollama server is up (/api/version returns 200)
    - ollamaModelReady: the configured model is fully downloaded (/api/tags)
    - ollamaModel: the model name being checked (for display)

    Handles UndefinedTable gracefully: if the service_heartbeats table does not
    exist yet (Flyway has not finished migrating), the error is logged at debug
    level and the thread retries on the next cycle. This covers the startup race
    where the worker starts before the API has run migrations.
    """
    while not stop_event.is_set():
        ollama_reachable = check_ollama_reachable(settings.ollama_url)
        ollama_model_ready = (
            check_ollama_model_ready(settings.ollama_url, settings.ollama_model)
            if ollama_reachable
            else False
        )

        details: dict[str, Any] = {
            "ollamaReachable": ollama_reachable,
            "ollamaModelReady": ollama_model_ready,
            "ollamaModel": settings.ollama_model,
        }

        try:
            upsert_heartbeat(instance_id, details)
        except Exception as exc:
            # UndefinedTable is expected during startup if the worker starts
            # before the API has finished running Flyway migrations. Log at
            # debug level so it doesn't spam the logs; the next cycle will retry.
            exc_msg = str(exc)
            if "does not exist" in exc_msg:
                log.debug("Heartbeat skipped: schema not ready yet (Flyway may still be running)")
            else:
                log.error("Failed to write heartbeat: %s", exc)

        if ollama_reachable and not ollama_model_ready:
            log.info("Ollama is up but model '%s' is not ready yet (still downloading?)", settings.ollama_model)

        stop_event.wait(timeout=settings.worker_poll_seconds)


def dispatch_job(job: dict[str, Any], engine: EngineWrapper) -> None:
    """
    Dispatch a claimed job to the appropriate handler based on kind.
    """
    kind = job["kind"]
    job_id = str(job["id"])

    log.info("Processing job %s kind=%s", job_id, kind)

    if kind == "analyze_game":
        from worker.analysis import analyze_game
        analyze_game(job, engine)
        return

    if kind == "generate_puzzles":
        from worker.puzzles import generate_puzzles
        generate_puzzles(job)
        return

    if kind == "review_game":
        from worker.review import review_game
        review_game(job)
        return

    raise NotImplementedError(f"No handler registered for job kind: {kind!r}")


def compute_retry_delay(attempts: int) -> int:
    """Return retry delay in seconds based on attempt count."""
    delays = {1: 0, 2: 300, 3: 1800}
    return delays.get(attempts, 1800)


def main() -> None:
    instance_id = get_instance_id()
    log.info("Worker starting. instance=%s", instance_id)

    # Start the heartbeat thread FIRST so the worker is visible on the status
    # page immediately, even before the schema is fully ready.
    stop_event = threading.Event()
    hb_thread = threading.Thread(
        target=heartbeat_loop,
        args=(instance_id, stop_event),
        daemon=True,
        name="heartbeat",
    )
    hb_thread.start()
    log.info("Heartbeat thread started")

    # Start the Stockfish engine
    engine = EngineWrapper()
    try:
        engine.start()
    except Exception as exc:
        log.error("Failed to start Stockfish: %s. Analysis jobs will fail until fixed.", exc)

    # Run the reaper after the heartbeat is running.
    reset_count = reset_stale_jobs()
    log.info("Reaper: reset %d stale job(s) on startup", reset_count)

    # Main claim loop
    log.info("Entering claim loop (poll every %ds)", settings.worker_poll_seconds)
    try:
        while True:
            try:
                job = claim_job(instance_id)
            except Exception as exc:
                log.error("Error claiming job: %s", exc)
                time.sleep(settings.worker_poll_seconds)
                continue

            if job is None:
                time.sleep(settings.worker_poll_seconds)
                continue

            job_id = str(job["id"])
            log.info("Claimed job id=%s kind=%s attempt=%d", job_id, job["kind"], job["attempts"])

            try:
                dispatch_job(job, engine)
                complete_job(job_id)
                log.info("Completed job id=%s kind=%s", job_id, job["kind"])
            except NotImplementedError as exc:
                # Expected in Phase 0: no handlers yet. Fail without retry.
                log.warning("No handler for job id=%s: %s", job_id, exc)
                fail_job(job_id, str(exc))
            except Exception as exc:
                log.error("Job id=%s failed: %s", job_id, exc, exc_info=True)
                delay = compute_retry_delay(job["attempts"])
                max_attempts = job.get("max_attempts", 3)
                if job["attempts"] >= max_attempts:
                    fail_job(job_id, str(exc))
                    log.error("Job id=%s exhausted retries, marked failed", job_id)
                else:
                    fail_job(job_id, str(exc), retry_after_seconds=delay)
                    log.info("Job id=%s will retry after %ds", job_id, delay)

    except KeyboardInterrupt:
        log.info("Worker shutting down")
    finally:
        stop_event.set()
        hb_thread.join(timeout=5)
        engine.stop()
        log.info("Worker stopped")


if __name__ == "__main__":
    main()
