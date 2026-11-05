# Local Development

## Prerequisites

- Docker Desktop (with Compose v2)
- Make
- Ollama installed natively on the host (`brew install ollama` on macOS)
- At least one Ollama model pulled: `ollama pull qwen3:8b`

The API and worker are built inside Docker. You do not need JDK, Python, or Gradle installed
on the host to run the app.

## Ollama Connectivity

Ollama runs natively on the host, not in Docker. The worker container reaches it via
`host.docker.internal:11434`. This requires two things in `docker-compose.yml`:

1. **`extra_hosts` mapping** on the worker service:
   ```yaml
   extra_hosts:
     - "host.docker.internal:host-gateway"
   ```
   Without this, `host.docker.internal` may not resolve inside the container on all Docker
   platforms. If Ollama shows as `down` on the Status page but `ollama list` works on the
   host, this mapping is missing or not taking effect.

2. **`OLLAMA_URL` environment variable** defaults to
   `http://host.docker.internal:11434`. Override it in `.env` if your Ollama instance
   runs on a different address.

The worker checks two things independently and reports them in the heartbeat:
- `ollamaReachable`: Ollama server is up (`GET /api/version`)
- `ollamaModelReady`: the configured model is fully downloaded (`GET /api/tags`)

If the model is still downloading, the Status page shows an amber "downloading" badge
instead of a red "down" badge, so you know to wait rather than debug.

## Quick Start

```bash
cp .env.example .env          # fill in DB_PASSWORD at minimum
make up                        # docker compose up --build -d
make logs                      # tail all service logs
```

Open http://localhost:5176. The Status page should show all services green within ~30 seconds.

## Make Targets

| Target         | What it does                                              |
|----------------|-----------------------------------------------------------|
| `make up`      | `docker compose up --build -d`                            |
| `make down`    | `docker compose down`                                     |
| `make logs`    | `docker compose logs -f`                                  |
| `make test`    | Run all tests (API Testcontainers + worker pytest)        |
| `make lint`    | Run ktlint (API) and ruff (worker)                        |
| `make migrate` | Apply pending Flyway migrations against the running DB    |
| `make seed`    | Load fixture games into the running DB                    |
| `make clean`   | `docker compose down -v` (removes volumes; destroys data) |

## Environment Variables

Copy `.env.example` to `.env` and fill in values. Never commit `.env`.

The `.env` file is loaded by Docker Compose automatically. Key variables:

| Variable             | Example value                           |
|----------------------|-----------------------------------------|
| DB_PASSWORD          | `changeme`                              |
| STOCKFISH_PATH       | `/usr/games/stockfish`                  |
| ANALYSIS_DEPTH       | `14`                                    |
| OLLAMA_MODEL         | `qwen3:8b`                              |
| CHESSCOM_USER_AGENT  | `ChessTrainer/1.0 contact@example.com`  |

## Service Ports

| Service  | Host port | Container port |
|----------|-----------|----------------|
| postgres | 5432      | 5432           |
| api      | 8084      | 8084           |
| web      | 5176      | 5176           |

The worker exposes no port.

## Hot Reload

- **Web**: Vite HMR is enabled. Edit files in `web/src/` and the browser updates immediately.
- **API**: Spring DevTools is not included. Restart the api container after code changes:
  `docker compose restart api` (or `make up` to rebuild).
- **Worker**: Restart after code changes: `docker compose restart worker`.

## Running Tests Locally

### API tests

```bash
cd api
./gradlew test
```

Requires Docker to be running (Testcontainers spins up a real Postgres).

### Worker tests

```bash
cd worker
uv run pytest
```

Requires Stockfish installed locally for engine integration tests, or use the Docker target:

```bash
docker compose run --rm worker pytest
```

## Database Access

Connect to the running Postgres with:

```bash
docker compose exec postgres psql -U chess_trainer -d chess_trainer
```

## Resetting the Database

```bash
make clean   # removes the pgdata volume
make up      # Flyway re-runs all migrations on fresh DB
```

## Adding a shadcn Component

```bash
cd web
pnpm dlx shadcn@latest add <component-name>
```

## Scaling the Worker

```bash
docker compose up --scale worker=2
```

Multiple worker instances claim different jobs via `SKIP LOCKED`. Each instance gets a unique
`WORKER_INSTANCE_ID` from its hostname.
