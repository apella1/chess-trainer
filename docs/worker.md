# Worker

## Overview

The worker is a Python process that runs the computationally intensive parts of the pipeline:
Stockfish analysis, puzzle generation, and LLM review requests. It is intentionally separate
from the Spring API so it can be scaled independently and so its heavy dependencies
(Stockfish, python-chess, Ollama client) do not touch the API container.

## Technology

| Library               | Version | Role                                      |
|-----------------------|---------|-------------------------------------------|
| Python                | 3.12    | Runtime                                   |
| psycopg[binary,pool]  | 3.x     | PostgreSQL driver                         |
| python-chess          | current | PGN parsing, board state, UCI engine control |
| pydantic              | 2.x     | Settings and output validation            |
| httpx                 | current | Ollama HTTP client                        |
| tenacity              | current | Retry logic for Ollama calls              |
| pytest                | current | Tests                                     |
| ruff                  | current | Linting and formatting                    |

## Source Layout

```
worker/
├── Dockerfile
├── pyproject.toml
└── src/worker/
    ├── main.py       — Entrypoint: claim loop, reaper, heartbeat thread
    ├── config.py     — Env-based settings (pydantic BaseSettings)
    ├── db.py         — ALL SQL in one place; no SQL in other modules
    ├── jobs.py       — claim(), complete(), fail(), retry()
    ├── engine.py     — Stockfish UCI wrapper
    ├── analysis.py   — Per-game analysis pipeline
    ├── winprob.py    — Centipawn → win probability, thresholds, classification
    ├── classify.py   — Mistake type detection (Phase 5)
    ├── puzzles.py    — Puzzle generation and quality filters
    ├── facts.py      — Builds the structured facts package for LLM
    ├── llm.py        — Ollama client, output schema, validation
    └── review.py     — Review pipeline
```

**Rule:** All SQL lives in `db.py`. Other modules call functions from `db.py`. This means
analysis, puzzle, and review logic can be tested without a real database by mocking `db.py`.

## Main Loop

```
startup:
  run reaper (reset stale running jobs)
  start heartbeat thread (writes service_heartbeats every N seconds)
  check Ollama reachability, include result in heartbeat

loop:
  claim one job
  if no job: sleep WORKER_POLL_SECONDS (default 5), continue
  dispatch to handler based on job.kind
  on success: complete(job), enqueue follow-on jobs
  on failure: fail(job, error), increment attempts
             if attempts >= max_attempts: leave as failed
             else: reset to pending with backoff delay
```

## Configuration

All configuration is via environment variables, loaded by `config.py` using pydantic
`BaseSettings`. No hardcoded values in any other module.

| Variable             | Default                                | Notes                     |
|----------------------|----------------------------------------|---------------------------|
| DB_URL               | (required)                             | `postgresql://user:pw@host:5432/db` |
| STOCKFISH_PATH       | `/usr/games/stockfish`                 |                           |
| ANALYSIS_DEPTH       | `14`                                   |                           |
| ANALYSIS_MULTIPV     | `3`                                    |                           |
| OLLAMA_URL           | `http://host.docker.internal:11434`    |                           |
| OLLAMA_MODEL         | `qwen3:8b`                             |                           |
| REVIEW_PROMPT_VERSION| `v1`                                   |                           |
| WORKER_POLL_SECONDS  | `5`                                    |                           |
| WORKER_INSTANCE_ID   | hostname (auto-generated if absent)    |                           |

## Heartbeat

The worker writes to `service_heartbeats` every `WORKER_POLL_SECONDS`. The row includes:

```json
{
  "ollamaReachable": true,
  "currentJobId": "abc-123",
  "currentJobKind": "analyze_game"
}
```

The Status page in the UI reads this row and shows the worker as:
- `ok` — heartbeat within last 30 seconds
- `stale` — heartbeat within last 5 minutes
- `down` — no heartbeat in over 5 minutes

## Stockfish Lifecycle

One Stockfish process per worker instance. Started on worker startup, kept alive for the
duration. On analysis of each position, `setoption` and `go depth N` commands are sent via
UCI. The engine is not restarted between games.

The engine name and version are read from the UCI `id name` line on startup and passed to
`db.py` when creating `analysis_runs` rows.

## Resource Constraint

Stockfish analysis and Ollama inference should not run simultaneously on a 24 GB machine.
The worker processes `analyze_game` and `generate_puzzles` jobs in one pass, then
`review_game` jobs in a second pass. This is controlled by priority ordering in the job
claim query.

## Testing

- Unit tests for `winprob.py` and `classify.py` use only fixture data (no DB, no engine).
- Integration tests for `analysis.py` use fixture PGN files in `fixtures/pgn/` and run
  Stockfish at a low depth (depth 5) for speed and determinism.
- LLM tests use recorded responses in `fixtures/expected/` and deliberately broken outputs
  to test validation rejection.
- No live chess.com API calls in any test.
