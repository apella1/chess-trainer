# Architecture Overview

## System Purpose

Chess Trainer is a personal chess improvement tool that turns your own chess.com games into
targeted training material. Rather than showing you what a 3500-rated engine would play, it
focuses on the kinds of mistakes that actually cost rating points at the 1100 level: hanging
pieces, missed one-to-three move tactics, and positions that were won but not converted.

## High-Level Data Flow

```
Browser (React/Vite)
        |
        | HTTP /api/*
        v
Spring Boot API  ──── Postgres ────  Python Worker
                                          |
                                          +── Stockfish (inside worker container)
                                          |
                                          +── Ollama (host machine, port 11434)
```

The browser never talks to the worker or to Ollama directly. All reads and writes go through
the Spring API. The worker is a background process that claims jobs from a Postgres table and
runs them to completion.

## Services

| Service  | Technology                       | Port | Notes                                      |
|----------|----------------------------------|------|--------------------------------------------|
| postgres | PostgreSQL 16                    | 5432 | Named volume `pgdata`; job queue table lives here |
| api      | Spring Boot, Kotlin, JDK 25      | 8084 | Owns all DDL via Flyway; the only process that exposes HTTP |
| worker   | Python 3.12                      | —    | Stateless; scale with `--scale worker=N`   |
| web      | React 19, Vite, Tailwind, shadcn | 5176 | Dev: Vite HMR; prod: static build served by nginx |
| ollama   | Host process                     | 11434 | Not in Compose; containers reach it at `host.docker.internal:11434` |

## Key Architectural Decisions

These decisions are intentional and should not be changed without an ADR.

1. **Monorepo.** One `docker compose up` starts everything. Cross-cutting changes land in one
   commit.

2. **Spring Boot owns the schema.** Flyway migrations in `api/` are the only place DDL runs.
   The worker reads and writes rows but never runs `CREATE` or `ALTER`.

3. **Postgres is the job queue.** A `SELECT ... FOR UPDATE SKIP LOCKED` pattern on
   `analysis_jobs` avoids a dependency on Redis or any message broker. Simple, debuggable,
   transactional.

4. **React talks only to Spring.** The worker and Ollama are internal. The browser is never
   aware of them.

5. **Ollama runs on the host.** Docker on macOS cannot use the Apple GPU. Keeping Ollama
   native and reaching it from containers via `host.docker.internal` gives full GPU access
   without any Docker workarounds.

6. **Everything is idempotent.** Games are unique on `(user_id, source, external_id)`.
   Re-syncing never creates duplicates. Jobs can be retried safely.

7. **Evaluations from the mover's perspective.** All centipawn and win-probability values in
   `move_evals` represent the position from the point of view of the player who is about to
   move. Positive means good for the mover. This is never mixed with White-perspective values.

8. **The LLM never computes chess facts.** The worker builds a structured facts package from
   engine output and passes it to Ollama. The LLM writes prose only. Its output is validated
   against the facts it received.

9. **No WebFlux, no Redis, no Spring AI, no Rust.** The plan explicitly excludes these.
   Deviating requires an ADR.

## Package Namespace

Kotlin: `me.apella.chesstrainer`  
Python worker: `worker` package under `src/`  
React: `src/` with feature folders mirroring API resources

## Environment Variables

All runtime configuration is injected via environment variables. See `.env.example` at the
repo root for the full list. No secrets are committed to git.
