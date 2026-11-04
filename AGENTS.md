# Agent Working Agreement

Rules for AI agents working on this codebase. Read `docs/architecture_overview.md` before
starting any task.

1. **One phase at a time.** Work on exactly the current phase. Do not build ahead.

2. **Respect architectural decisions.** The decisions in `docs/architecture_overview.md` and
   `docs/adr/` are intentional. If a task seems to require breaking one, stop and write a new
   ADR in `docs/adr/` instead of working around it.

3. **Flyway owns the schema.** Only Flyway migrations in `api/src/main/resources/db/migration/`
   change the schema. Never edit an applied migration — always add a new one.

4. **Worker SQL lives in `db.py` only.** All SQL in the worker belongs in
   `worker/src/worker/db.py`. Other modules call functions from `db.py`.

5. **The LLM never computes chess facts.** Evaluations, best moves, and mistake types come
   from the engine pipeline. The LLM only phrases them as prose.

6. **Tests with every change.** Use fixtures in `fixtures/`, not the live chess.com API.
   No live network calls in tests.

7. **Verify before declaring done.** Before reporting a phase complete:
   - Cold `docker compose up --build` works from a clean checkout
   - `make test` and `make lint` pass
   - The acceptance criteria for the phase are satisfied
   - README documents how to demo it

8. **When something says verify** (library versions, Ollama request fields, Stockfish
   packaging): check current official documentation and note what you found.

9. **Ask before adding anything new.** Do not add any dependency, service, or table not
   listed in `docs/` without writing an ADR first.

10. **Commit conventions.** Use Angular Conventional Commits for all commits:
    ```
    <type>(<scope>): <short summary>

    [optional body]
    ```
    Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`
    Scopes: `api`, `worker`, `web`, `db`, `infra`, `docs`

    Examples:
    - `feat(api): add /api/status endpoint`
    - `feat(db): add V1 Flyway migration for users and heartbeats`
    - `chore(infra): configure docker-compose with all four services`
