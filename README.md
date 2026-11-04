# Chess Trainer

A personal chess improvement tool that turns your chess.com games into targeted training
material. Analyzes your mistakes with Stockfish, generates puzzles from your own games,
and writes coaching reviews with a local LLM.

## Quick Start

```bash
# 1. Install prerequisites
#    - Docker Desktop (with Compose v2)
#    - Ollama: brew install ollama && ollama pull qwen3:8b

# 2. Configure environment
cp .env.example .env
# Edit .env — set DB_PASSWORD and CHESSCOM_USER_AGENT at minimum

# 3. Start everything
make up

# 4. Open the app
open http://localhost:5173
```

The Status page shows whether all services are running. The worker writes a heartbeat every
few seconds; if Ollama is reachable, that is shown too.

## Make Targets

| Command       | What it does                          |
|---------------|---------------------------------------|
| `make up`     | Build and start all services          |
| `make down`   | Stop all services                     |
| `make logs`   | Tail logs for all services            |
| `make test`   | Run all tests                         |
| `make lint`   | Run linters (ktlint + ruff)           |
| `make clean`  | Stop services and remove all volumes  |

## Architecture

```
Browser (React + Vite)
        │  /api/*
        ▼
Spring Boot API (port 8080)
        │
        ▼
   PostgreSQL (port 5432) ◄─── Python Worker
                                     │
                               Stockfish (in container)
                               Ollama (host, port 11434)
```

See `docs/architecture_overview.md` for details.

## Documentation

| Document | Contents |
|---|---|
| [docs/architecture_overview.md](docs/architecture_overview.md) | System design and key decisions |
| [docs/data_model.md](docs/data_model.md) | All database tables and columns |
| [docs/api_design.md](docs/api_design.md) | API endpoints and conventions |
| [docs/job_queue.md](docs/job_queue.md) | Job queue design and retry logic |
| [docs/chess_analysis.md](docs/chess_analysis.md) | Stockfish analysis and mistake classification |
| [docs/llm_reviews.md](docs/llm_reviews.md) | LLM review pipeline and validation |
| [docs/frontend.md](docs/frontend.md) | Frontend stack and conventions |
| [docs/worker.md](docs/worker.md) | Python worker design and configuration |
| [docs/testing_strategy.md](docs/testing_strategy.md) | Testing approach per service |
| [docs/local_development.md](docs/local_development.md) | Dev environment setup |
| [docs/adr/](docs/adr/) | Architecture Decision Records |

## Build Status

Phase 0 (walking skeleton) complete:
- ✅ Docker Compose wires all four services with healthchecks
- ✅ Flyway V1 migration creates `users` and `service_heartbeats`
- ✅ Spring API exposes `/api/status` and `/actuator/health`
- ✅ Worker writes heartbeats and checks Ollama reachability
- ✅ Status page shows all services with live heartbeat age
