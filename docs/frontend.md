# Frontend

## Stack

| Library          | Version  | Role                                          |
|------------------|----------|-----------------------------------------------|
| React            | 19       | UI framework                                  |
| TypeScript       | 5.x      | Type safety                                   |
| Vite             | 7.x      | Build tool and dev server                     |
| Tailwind CSS     | 4.x      | Utility-first styling                         |
| shadcn/ui        | current  | Accessible component primitives (new-york style) |
| React Router     | 6.x      | Client-side routing                           |
| TanStack Query   | 5.x      | Server state management, polling, caching     |
| react-chessboard | current  | Interactive chess board component             |
| chess.js         | current  | Move validation, PGN parsing, board state     |
| Recharts         | current  | Win probability chart, dashboard graphs       |
| Redux Toolkit    | 2.x      | Client-only UI state (not server state)       |

## State Management Split

- **Server state** (games, puzzles, jobs, stats): TanStack Query exclusively. No Redux for
  server data. This gives automatic caching, background refetching, and polling with a single
  hook.
- **Client state** (board position during replay, current puzzle state, UI mode): Redux
  Toolkit. Kept minimal; most state lives in TanStack Query.

## Routes

| Path             | Page         | Phase |
|------------------|--------------|-------|
| /                | Status       | 0     |
| /games           | Games        | 1     |
| /games/:id       | GameDetail   | 1-2   |
| /train           | Train        | 3     |
| /weaknesses      | Weaknesses   | 5     |
| /sessions        | Sessions     | 6     |
| /settings        | Settings     | 7     |

## Key Components

| Component     | Purpose                                                  | Phase |
|---------------|----------------------------------------------------------|-------|
| Board         | react-chessboard with chess.js for PGN replay            | 1     |
| MoveList      | SAN notation with clock times and classification badges  | 2     |
| EvalChart     | Win probability per ply (Recharts line chart)            | 2     |
| ReviewPanel   | LLM review text, model/prompt version tag, regenerate    | 4     |
| PuzzleBoard   | Move entry, hint, retry, refutation display              | 3     |
| JobProgress   | Polls `/api/jobs/summary`, shows counts by status        | 2     |

## API Communication

All HTTP calls go through typed client files in `src/api/`, one file per API resource
(e.g. `src/api/games.ts`, `src/api/puzzles.ts`). These files export functions that TanStack
Query hooks call. No `fetch` calls outside of `src/api/`.

All response types are defined in `src/types/` and mirror the Spring DTOs. If a DTO changes,
the TypeScript type must be updated.

## Polling

Job progress and worker status are polled. Polling intervals are defined in one place:
`src/lib/polling.ts`. Default:
- Job summary: every 3 seconds while any job is pending or running
- Worker status: every 10 seconds

## Dev Proxy

Vite proxies `/api` to `http://api:8080` in development. This means the React dev server and
the Spring API are on the same origin from the browser's perspective, avoiding CORS in dev.

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': 'http://localhost:8080'
  }
}
```

In Docker Compose, the web service uses `http://api:8080` as the proxy target.

## Conventions

- All imports use the `@/` alias (resolves to `src/`).
- Component files use PascalCase, hook files use camelCase prefixed with `use`.
- No inline styles. Tailwind utilities only.
- Accessible by default: shadcn components are built on Radix UI primitives which handle
  keyboard navigation and ARIA automatically.
