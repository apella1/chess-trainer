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
open http://localhost:5176
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
| [docs/plan.md](docs/plan.md) | Shared product scope, architecture, data model, and conventions |
| [docs/plan/](docs/plan/) | Phase-by-phase deliverables, demos, and acceptance checks |
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

Phase 0 ✅ [Walking skeleton](docs/plan/phase-0-walking-skeleton.md)
- Docker Compose, Flyway V1, `/api/status`, worker heartbeat, Status page

Phase 1 ✅ [Game library](docs/plan/phase-1-game-library.md)
- chess.com sync (incremental), PGN upload, games list with filters, PGN replay viewer
- Tempo branding, board themes, click-through from landing page

Phase 2 ✅ [Engine analysis](docs/plan/phase-2-engine-analysis.md)
- Stockfish depth-14 analysis, win-probability classification (Lichess formula)
- Moves, eval chart, mistake highlighting in game detail view
- Job progress indicator, clock data from PGN

Phase 3 ✅ [Puzzles from your mistakes](docs/plan/phase-3-puzzles.md)
- Quality filters (unique solution ≥15% gap, decided position exclusion, FEN dedup)
- Theme grouping, click-to-move with valid square dots, drag-and-drop
- Restart button, attempt persistence

Phase 4 ✅ [Local LLM game reviews](docs/plan/phase-4-game-reviews.md)
- Facts package → Ollama (qwen3:8b) → structured JSON review with validation
- ReviewPanel in game detail: summary, key moments, strengths, habit to fix
- Regenerate button, model/prompt version badge

Phase 5 (planned) — [Level-aware weakness profile](docs/plan/phase-5-weakness-profile.md)
Phase 6 (planned) — [Deliberate practice loop](docs/plan/phase-6-practice-loop.md)
Phase 7 (planned) — [Multi-user auth](docs/plan/phase-7-multi-user.md)
Phase 8 (planned) — [Extensions](docs/plan/phase-8-extensions.md)
