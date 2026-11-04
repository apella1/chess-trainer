# API Design

## Principles

- All endpoints are under `/api`.
- Spring Boot Actuator endpoints remain at `/actuator`.
- Responses use consistent JSON shapes: a data envelope for collections, a flat object for
  single resources, and a standard error body for failures.
- Pagination uses `page` and `size` query parameters. Responses include `totalElements`,
  `totalPages`, `page`, and `size`.
- All timestamps are ISO-8601 UTC strings.
- Auth is not enforced until Phase 7. Until then, a `X-User-Id` header or a default user is
  used for development.

## Error Body

All non-2xx responses return:

```json
{
  "status": 404,
  "error": "Not Found",
  "message": "Game abc123 not found",
  "path": "/api/games/abc123",
  "timestamp": "2026-01-01T12:00:00Z"
}
```

## Endpoints

### Health and Status

| Method | Path                | Purpose                                     | Phase |
|--------|---------------------|---------------------------------------------|-------|
| GET    | /actuator/health    | Spring Boot health (db, disk)               | 0     |
| GET    | /api/status         | Composite: api, db, worker heartbeat, Ollama | 0    |

`GET /api/status` response:

```json
{
  "api": "ok",
  "database": "ok",
  "worker": {
    "status": "ok",
    "lastSeenSeconds": 4,
    "details": { "ollamaReachable": true }
  },
  "ollama": "ok"
}
```

Worker status is `ok` if last heartbeat was under 30 seconds ago, `stale` under 5 minutes,
`down` otherwise. Ollama status is taken from the worker's latest heartbeat details.

### Sync

| Method | Path            | Purpose                                          | Phase |
|--------|-----------------|--------------------------------------------------|-------|
| POST   | /api/sync       | Start a chess.com sync for `{"username":"..."}` | 1     |
| GET    | /api/sync/{id}  | Progress of a sync                              | 1     |

### Games

| Method | Path                  | Purpose                                 | Phase |
|--------|-----------------------|-----------------------------------------|-------|
| POST   | /api/games/upload     | PGN file upload (multipart/form-data)  | 1     |
| GET    | /api/games            | Paginated list with filters             | 1     |
| GET    | /api/games/{id}       | Single game with PGN; evals from Phase 2 | 1-2 |

`GET /api/games` query parameters: `result`, `color`, `timeClass`, `page`, `size`.

### Jobs

| Method | Path               | Purpose                        | Phase |
|--------|--------------------|--------------------------------|-------|
| GET    | /api/jobs/summary  | Counts by status and kind      | 2     |

### Puzzles

| Method | Path                        | Purpose                              | Phase |
|--------|-----------------------------|--------------------------------------|-------|
| GET    | /api/puzzles/next           | Next puzzle (filters: type, theme)   | 3     |
| POST   | /api/puzzles/{id}/attempts  | Record an attempt                    | 3     |

### Reviews

| Method | Path                             | Purpose                         | Phase |
|--------|----------------------------------|---------------------------------|-------|
| GET    | /api/games/{id}/review           | Latest stored review            | 4     |
| POST   | /api/games/{id}/review/regenerate | Enqueue a new review job        | 4     |

### Stats

| Method | Path                  | Purpose                                | Phase |
|--------|-----------------------|----------------------------------------|-------|
| GET    | /api/stats/weaknesses | Ranked weaknesses by rate per 100 moves | 5    |
| GET    | /api/stats/trends     | Per-category rate over rolling windows  | 6    |

### Practice

| Method | Path                  | Purpose                          | Phase |
|--------|-----------------------|----------------------------------|-------|
| GET    | /api/sessions/today   | Today's practice queue           | 6     |
| POST   | /api/sessions         | Start or record a session        | 6     |

## Package Structure

Each feature in the API is a self-contained package under `me.apella.chesstrainer`:

```
me.apella.chesstrainer/
├── config/        — CORS, Jackson, scheduling, properties
├── common/        — error body, pagination, time utilities, ID helpers
├── users/         — entity, repository, service
├── status/        — /api/status controller and service
├── sync/          — chess.com HTTP client, sync service and controller
├── games/         — game entity, repository, controller, DTOs
├── jobs/          — job entity, enqueue service, summary endpoint
├── puzzles/       — puzzle queries, attempt recording
├── practice/      — spaced repetition, sessions (Phase 6)
├── reviews/       — review read and regenerate endpoints
└── stats/         — weakness and trend queries
```

Each package contains its own controller, service, repository, entity, and DTOs. No shared
layer packages (no `controllers/`, no `services/`, no `repositories/` directories).

## CORS

In development, `http://localhost:5173` (Vite dev server) is allowed. In production the
allowed origin is the configured app domain. Configured in `CorsConfig.kt`.

## Security

Spring Security is included from day one but configured permissively for Phases 0–6:
all `/api/**` and `/actuator/**` routes are open. Phase 7 introduces authentication and
per-user data isolation.
