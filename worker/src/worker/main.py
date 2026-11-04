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


def heartbeat_loop(instance_id: str, stop_event: threading.Event) -> None:
    """
    Background thread: write a heartbeat row every WORKER_POLL_SECONDS.
    Includes Ollama reachability in the details payload.
    """
    while not stop_event.is_set():
        ollama_ok = check_ollama_reachable(settings.ollama_url)
        details: dict[str, Any] = {"ollamaReachable": ollama_ok}

        try:
            upsert_heartbeat(instance_id, details)
        except Exception as exc:
            log.error("Failed to write heartbeat: %s", exc)

        stop_event.wait(timeout=settings.worker_poll_seconds)


def dispatch_job(job: dict[str, Any]) -> None:
    """
    Dispatch a claimed job to the appropriate handler based on kind.

    Phase 0: no job kinds are registered yet. Jobs will be added in Phase 2+.
    """
    kind = job["kind"]
    job_id = str(job["id"])

    log.info("Processing job %s kind=%s", job_id, kind)

    # Handlers will be registered here as phases are built.
    # Example (Phase 2):
    #   if kind == "analyze_game":
    #       from worker.analysis import analyze_game
    #       analyze_game(job)
    #       return

    raise NotImplementedError(f"No handler registered for job kind: {kind!r}")


def compute_retry_delay(attempts: int) -> int:
    """Return retry delay in seconds based on attempt count."""
    delays = {1: 0, 2: 300, 3: 1800}
    return delays.get(attempts, 1800)


def main() -> None:
    instance_id = get_instance_id()
    log.info("Worker starting. instance=%s", instance_id)

    # Run reaper before starting the loop
    reset_count = reset_stale_jobs()
    log.info("Reaper: reset %d stale job(s) on startup", reset_count)

    # Start heartbeat thread
    stop_event = threading.Event()
    hb_thread = threading.Thread(
        target=heartbeat_loop,
        args=(instance_id, stop_event),
        daemon=True,
        name="heartbeat",
    )
    hb_thread.start()
    log.info("Heartbeat thread started")

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
                dispatch_job(job)
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
        log.info("Worker stopped")


if __name__ == "__main__":
    main()
