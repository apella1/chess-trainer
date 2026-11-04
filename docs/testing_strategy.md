# Testing Strategy

## Principles

- Tests run without live external services. No chess.com API calls, no live Ollama, no
  network in CI.
- Fixtures live in `fixtures/`. Fixture PGN files, chess.com JSON responses, and expected
  analysis outputs are committed to the repo.
- Tests are deterministic. Engine tests use low depth (5) and known fixture positions so
  the same classification is produced on every run.
- Tests accompany every feature change. A PR that adds a feature without tests will not
  be merged.

## API Tests (Kotlin, Spring Boot, Testcontainers)

**Framework:** JUnit 5 + Spring Boot Test + Testcontainers (PostgreSQL)  
**Location:** `api/src/test/kotlin/me/apella/chesstrainer/`

Pattern:
- One base test class `IntegrationTestBase` that starts a Testcontainers Postgres, applies
  all Flyway migrations, and exposes a `MockMvc` instance.
- Tests extend this base class.
- HTTP layer tests use `MockMvc` to call controllers and assert response shapes.
- No live chess.com network calls. The chess.com HTTP client is mocked or replaced with a
  fixture-loading implementation.

Coverage targets:
- Sync idempotency: re-syncing the same fixture response never duplicates `games` rows.
- Malformed PGN upload: returns 400 with a clear error body.
- `/api/status`: returns correctly shaped response with all fields.
- Job enqueue: sync creates one `analyze_game` job per new game.

## Worker Tests (Python, pytest)

**Framework:** pytest  
**Location:** `worker/tests/`

Test categories:

### Unit tests (no DB, no engine)

- `test_winprob.py` — centipawn to win% conversion; mate scores; boundary values.
- `test_classify.py` — mistake type detection from fixture board positions.
- `test_puzzles.py` — quality filter logic (uniqueness, decided position check, deduplication).
- `test_llm.py` — validation of LLM output schema:
  - valid response passes validation
  - missing `key_moments` field fails
  - ply not in facts package fails
  - san not matching facts package fails
  - hallucinated evaluation number fails
  - retry logic triggers on first two failures

### Integration tests (real Stockfish, fixture PGNs, no DB)

- `test_analysis.py` — runs analysis pipeline on games in `fixtures/pgn/` at depth 5 and
  compares classifications against `fixtures/expected/` JSON files.
- Engine tests are marked `@pytest.mark.engine` and skipped if Stockfish is not on `PATH`.

### DB integration tests (real Postgres, via Docker)

- `test_db.py` — claim loop, reaper, retry backoff; uses a real DB via environment variable.
- Run with: `docker compose run --rm worker pytest -m db`

## Frontend Tests (TypeScript, Vitest, Testing Library)

**Framework:** Vitest + React Testing Library  
**Location:** `web/src/**/*.test.tsx`

Coverage targets:
- API client functions: mock `fetch`, assert correct URLs and request shapes.
- Component rendering: Status page shows correct badges for ok/stale/down states.
- Puzzle board: move entry triggers attempt recording.
- Board replay: clicking moves advances the position correctly.

## End-to-End Smoke Test

A shell script in `scripts/smoke_test.sh` that:
1. Starts the full stack with `docker compose up --build -d`
2. Waits for `/api/status` to return ok
3. Uploads a three-game fixture PGN
4. Polls `/api/jobs/summary` until all jobs are done
5. Asserts a `game_reviews` row exists for each game
6. Exits 0 on success, 1 on failure

This is run manually before declaring a phase complete. It is not part of CI by default
because it requires Ollama on the host.

## CI

GitHub Actions (or equivalent) runs on every push:
- `make test` — API Testcontainers tests + worker pytest (unit + engine at low depth)
- `make lint` — ktlint + ruff

The smoke test is not in CI because it requires a GPU host with Ollama.

## Fixtures

`fixtures/pgn/`:
- `simple_game.pgn` — Short game with one obvious blunder, used for quick tests.
- `clock_game.pgn` — Game with clock comments (`[%clk h:mm:ss]`), tests clock parsing.
- `opening_only.pgn` — Game that ends in the opening, tests early-termination handling.

`fixtures/expected/`:
- JSON files matching PGN fixture names, containing expected move classifications.
- Updated by running `scripts/update_fixtures.sh` with the new engine settings, then
  reviewing the diff before committing.
