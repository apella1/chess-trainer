Chess Trainer: Build Plan and Agent Context
A personal chess training app built from your own chess.com games. Version 2 of the plan, written for a human reader and for an AI coding agent.
1. How to use this document
• This is the source of truth for scope, architecture, data model and phases. Export it as Markdown and commit it as docs/PLAN.md. Copy section 15 into AGENTS.md at the repo root.
• Build one phase at a time. Every phase ends in a runnable app (docker compose up), and no phase depends on a later one.
• Where this document says verify, check current official docs (Spring Boot, Ollama, chess.com API, Stockfish packaging) instead of trusting memory.
• Do not add dependencies, tables, endpoints or services that are not listed here without writing a short ADR in docs/adr/.
2. The problem
User: a ~1100 rapid player (range 1050-1150) on chess.com Premium who wants to improve faster and who also wants to learn the chess software ecosystem by building the tool.
Why existing tools fall short:
• Engine analysis reports what a 3500-rated engine would play. At 1100, most rating loss comes from hanging pieces and missed 1-3 move tactics, not subtle positional errors, so raw engine output is mostly noise.
• Generic puzzle sets are not tied to the player's own recurring mistakes.
• Feedback is numbers ("-2.4") instead of explanations.
• Nothing closes the loop: the player never learns whether practice reduces mistakes in real games.
What the app does:
1. Imports games from chess.com (public API) with PGN upload as a fallback.
2. Analyzes every move with Stockfish and converts evaluations into win-probability loss so errors are judged sensibly.
3. Turns the user's own mistakes into solvable puzzles with quality filters.
4. Writes a local-LLM review for every analyzed game and saves it.
5. Classifies mistakes by type and builds a weakness profile using error rates.
6. Schedules deliberate practice (spaced repetition, targeted sessions) and measures whether real-game error rates fall.
7. Is multi-user ready so another person can enter a username and get the same experience.
Success metrics:
• Puzzle success rate stays between 70% and 80%.
• Blunder rate per 100 moves in the top weakness categories falls over 6-8 weeks of real games.
• A new user can onboard with only a username and no manual steps.
Non-goals (for now): playing games, writing a chess engine, mobile apps, Rust, real-time analysis during live games, paid tiers.
3. Design decisions (each is an ADR seed)
1. Monorepo. One repo, one docker compose up, one commit for cross-cutting changes.
2. Spring Boot owns the schema. Only Flyway migrations in api/ create or alter tables. The worker reads and writes rows but never runs DDL.
3. Postgres is the job queue. A table plus SELECT ... FOR UPDATE SKIP LOCKED. No Redis or broker.
4. React talks only to Spring. The worker and Ollama are never exposed to the browser.
5. Ollama runs natively on the host. Docker on macOS cannot use the Apple GPU. Containers reach it at http://host.docker.internal:11434.
6. Everything is idempotent. Games are unique on (user_id, source, external_id). Re-syncing never duplicates. Jobs can be retried safely.
7. Everything derived is versioned. Analysis stores engine name, version, depth and multi-PV. Reviews store model and prompt version, so output can be regenerated and compared.
8. Evaluations are stored from the mover's perspective (positive means good for the side that just moved or is about to move, as named in the column). Never mix White-perspective and mover-perspective values in one table.
9. The LLM never computes chess facts. It receives a structured facts package and writes prose. Its output is validated against that package.
10. Level-aware by default. Prefer error types and short tactics over deep engine lines.
11. Only the user's moves are "mistakes". The opponent's errors become missed opportunities when the user failed to punish them.
4. Architecture and data flow
React (Vite)  -->  Spring Boot API  -->  Postgres  <--  Python worker (python-chess + Stockfish)
                                                              |
                                                              +--> Ollama (host, :11434)
Pipeline for one game:
1. User triggers a sync. Spring fetches chess.com monthly archives and inserts new games rows, then inserts one analyze_game job per new game.
2. The worker claims an analyze_game job, parses the PGN with python-chess, writes moves, runs Stockfish on each position, writes move_evals, classifies moves and writes mistakes.
3. On success the worker enqueues generate_puzzles for the game, then review_game.
4. generate_puzzles creates puzzles rows from qualifying mistakes and missed opportunities.
5. review_game builds the facts package, calls Ollama, validates the JSON and writes game_reviews.
6. The UI reads results through Spring and polls job progress.
Job lifecycle: pending -> running -> done | failed. A failed job retries up to max_attempts (default 3) with a growing delay. A reaper in the worker resets running jobs whose locked_at is older than 15 minutes.
5. Technology choices and software bill of materials
Versions: use the current stable release of each at project start and pin them. Verify exact artifact names when generating the Spring project.
Area
Component
Role
License
Phase
Runtime
Docker Engine, Docker Compose v2
Local orchestration
Apache-2.0
0
Database
PostgreSQL 16
Store and job queue
PostgreSQL License
0
API
JDK 21 (Temurin), Kotlin 2.x, Gradle (Kotlin DSL)
Build and language
GPLv2+CE / Apache-2.0
0
API
Spring Boot (current stable)
Framework
Apache-2.0
0
API
spring-boot-starter-web, -actuator, -validation, -data-jpa
REST, health, validation, persistence
Apache-2.0
0-1
API
postgresql JDBC driver
DB driver
BSD-2
0
API
Flyway (flyway-core, flyway-database-postgresql)
Migrations
Apache-2.0
0
API
jackson-module-kotlin, kotlin-reflect
JSON and Kotlin support
Apache-2.0
0
API
Gradle plugins kotlin("plugin.spring"), kotlin("plugin.jpa")
Open classes, JPA no-arg constructors
Apache-2.0
0
API
spring-boot-starter-security
Auth and per-user isolation
Apache-2.0
7
API tests
spring-boot-starter-test, Testcontainers (postgresql), MockMvc
Tests against real Postgres
MIT / EPL-2.0
1
API quality
ktlint or detekt
Lint
MIT / Apache-2.0
0
Frontend
React, TypeScript, Vite
UI
MIT / Apache-2.0 / MIT
0
Frontend
React Router, TanStack Query
Routing, server state and polling
MIT
1
Frontend
react-chessboard, chess.js
Board, move validation, PGN replay
MIT / BSD-2
1
Frontend
Recharts
Eval graph, dashboards
MIT
2
Frontend
Tailwind CSS
Styling
MIT
0
Frontend tests
Vitest, Testing Library
Unit and component tests
MIT
1
Worker
Python 3.12, uv (or pip)
Runtime and deps
PSF / MIT-Apache
0
Worker
psycopg[binary,pool] v3
DB access
LGPL-3.0
0
Worker
python-chess
Boards, PGN, UCI engine control
GPL-3.0
2
Worker
Stockfish (Linux arm64 build, installed in image)
Engine
GPL-3.0
2
Worker
pydantic, httpx, tenacity
Validation, Ollama HTTP client, retries
MIT / BSD / Apache-2.0
2-4
Worker quality
pytest, ruff
Tests and lint
MIT
2
LLM
Ollama (host) with qwen3:8b or qwen3:14b (fallback llama3.1:8b)
Review writer
MIT / Apache-2.0 / Llama community
4
Optional
Maia weights + lc0
Human-like move prediction
GPL-3.0
5
Data
Lichess chess-openings (ECO names)
Opening names
CC0
5
Data
Lichess puzzle database
Supplementary puzzles
CC0
8
Source
chess.com Public API
Games
Read their terms
1
Not used, on purpose: WebFlux, Redis or message brokers, Spring AI, Spring Batch, Rust, a separate FastAPI service.
License note: Stockfish and python-chess are GPL-3.0. Hosting them as a service is fine. If the project is ever distributed (for example as a downloadable image), review GPL obligations first. Keeping the worker a separate process with a clear boundary helps.
6. Repository layout
chess-trainer/
├── README.md
├── AGENTS.md                     # rules for AI agents (from section 15)
├── Makefile                      # up, down, test, lint, migrate, seed
├── docker-compose.yml
├── docker-compose.override.yml   # dev: Vite HMR, source mounts
├── .env.example
├── docs/
│   ├── PLAN.md                   # this document
│   ├── data-model.md
│   └── adr/                      # 0001-monorepo.md, ...
├── fixtures/
│   ├── pgn/                      # small sample games incl. one with clocks
│   └── expected/                 # expected eval/classification outputs for tests
├── scripts/                      # seed data, one-off tools
├── api/
│   ├── Dockerfile
│   ├── build.gradle.kts
│   ├── settings.gradle.kts
│   └── src/
│       ├── main/kotlin/com/chesstrainer/
│       │   ├── Application.kt
│       │   ├── config/           # properties, CORS, Jackson, scheduling
│       │   ├── common/           # errors, pagination, time, ids
│       │   ├── users/            # entity, repository, service
│       │   ├── sync/             # chess.com client, sync service, controller
│       │   ├── games/            # entities, queries, controller, DTOs
│       │   ├── jobs/             # job entity, enqueue service, summary endpoint
│       │   ├── puzzles/          # puzzle queries, attempt recording
│       │   ├── practice/         # spaced repetition, sessions (Phase 6)
│       │   ├── reviews/          # review read/regenerate endpoints
│       │   └── stats/            # weakness and trend queries
│       ├── main/resources/
│       │   ├── application.yml
│       │   └── db/migration/     # V1__init.sql, V2__games.sql, ...
│       └── test/kotlin/...       # per-feature tests, Testcontainers base class
├── worker/
│   ├── Dockerfile                # python:3.12-slim + stockfish
│   ├── pyproject.toml
│   ├── src/worker/
│   │   ├── main.py               # entrypoint: claim loop, reaper, heartbeat
│   │   ├── config.py             # env-based settings (pydantic)
│   │   ├── db.py                 # ALL SQL lives here (repository layer)
│   │   ├── jobs.py               # claim, complete, fail, retry
│   │   ├── engine.py             # Stockfish UCI wrapper
│   │   ├── analysis.py           # per-game analysis pipeline
│   │   ├── winprob.py            # centipawn to win-probability, thresholds
│   │   ├── classify.py           # mistake types and phases (Phase 5)
│   │   ├── puzzles.py            # puzzle generation and quality filters
│   │   ├── facts.py              # builds the facts package for reviews
│   │   ├── llm.py                # Ollama client, schema, validation
│   │   └── review.py             # review pipeline
│   └── tests/                    # pytest; engine tests use fixtures and low depth
└── web/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.ts            # dev proxy /api -> api:8080
    └── src/
        ├── main.tsx
        ├── app/                  # router, providers
        ├── api/                  # typed client, one file per resource
        ├── pages/                # Status, Games, GameDetail, Train, Weaknesses, Sessions, Settings
        ├── components/           # Board, MoveList, EvalChart, ReviewPanel, PuzzleBoard, JobProgress
        ├── hooks/
        ├── lib/                  # formatting, chess helpers
        └── types/
Rules for the layout: Kotlin code is organized by feature, not by layer (each feature package holds its controller, service, repository, entity and DTOs). The worker's SQL lives only in db.py, so analysis, puzzle and review logic can be tested without a database.
7. Local runtime
Service
Image / source
Port
Notes
postgres
postgres:16
5432
Named volume pgdata, healthcheck pg_isready
api
./api
8080
Depends on postgres healthy; healthcheck on /actuator/health
worker
./worker
none
Depends on postgres healthy; scale with --scale worker=N
web
./web
5173
Vite dev server in dev; static build in prod-like mode
Ollama
host process
11434
Not in Compose
Environment variables (.env.example): DB_URL, DB_USER, DB_PASSWORD, STOCKFISH_PATH, ANALYSIS_DEPTH (default 14), ANALYSIS_MULTIPV (default 3), OLLAMA_URL (http://host.docker.internal:11434), OLLAMA_MODEL (default qwen3:8b), REVIEW_PROMPT_VERSION (default v1), CHESSCOM_USER_AGENT (include a contact address), WORKER_POLL_SECONDS.
Stockfish in the image: install via the distro package or a downloaded arm64 release, then record the engine name and version from the UCI id name line on every analysis run. Verify the packaged version is acceptable.
8. Data model
Timestamps are timestamptz in UTC. Primary keys are UUIDs unless noted.
• users: id, chesscom_username (unique), display_name, rating_band (int, nullable), created_at.
• games: id, user_id, source (default chesscom), external_id (chess.com game UUID), url, pgn, played_at, time_class (rapid, blitz, bullet, daily), time_control, user_color, result (win, loss, draw), termination, user_rating, opp_rating, opp_username, eco, opening_name, analysis_status (none, queued, running, done, failed). Unique: (user_id, source, external_id).
• moves: id, game_id, ply, color, san, uci, fen_before, fen_after, clock_ms_remaining, time_spent_ms. Unique: (game_id, ply). Created by the worker during analysis.
• analysis_runs: id, game_id, engine_name, engine_version, depth, multipv, status, created_at.
• move_evals: id, run_id, move_id, eval_before_cp, eval_after_cp, mate_before, mate_after (all from the mover's perspective), best_uci, best_eval_cp, second_best_eval_cp, pv_json (jsonb), win_pct_before, win_pct_after, win_pct_loss, classification (book, best, good, inaccuracy, mistake, blunder).
• mistakes: id, game_id, user_id, move_eval_id, kind (mistake, missed_opportunity), type (see section 10), tags (text[]), phase (opening, middlegame, endgame), severity, material_swing_cp.
• puzzles: id, user_id (null for global), source (own_game, lichess), source_mistake_id, fen, side_to_move, solution_uci (text[]), themes (text[]), difficulty_est, active.
• puzzle_attempts: id, puzzle_id, user_id, solved, moves_tried (jsonb), time_ms, hints_used, attempted_at.
• review_schedule: primary key (puzzle_id, user_id), box, due_at, last_result, streak.
• game_reviews: id, game_id, run_id, model, prompt_version, facts_json (jsonb), review_json (jsonb), review_text, validation_status (ok, flagged), created_at. Unique: (game_id, model, prompt_version).
• analysis_jobs: id, user_id, game_id, kind (analyze_game, generate_puzzles, review_game), status, attempts, max_attempts, locked_by, locked_at, last_error, payload (jsonb), created_at, started_at, finished_at. Partial index on status = 'pending'.
• service_heartbeats: service, instance, last_seen, details (jsonb). Used by the status page.
Indexes to add early: games(user_id, played_at desc), moves(game_id, ply), mistakes(user_id, type), puzzles(user_id, active), review_schedule(user_id, due_at).
9. API surface (Spring, all under /api)
Method and path
Purpose
Phase
GET /actuator/health, GET /api/status
Health of api, db, worker, Ollama
0
POST /api/sync {username}
Start a sync, returns 202 and a sync id
1
GET /api/sync/{id}
Sync progress
1
POST /api/games/upload
PGN upload (multipart)
1
GET /api/games
List with filters (result, color, timeClass) and paging
1
GET /api/games/{id}
Game with PGN, and from Phase 2 moves, evals, mistakes
1-2
GET /api/jobs/summary
Counts by status and kind
2
GET /api/puzzles/next
Next puzzle (filters: type, theme)
3
POST /api/puzzles/{id}/attempts
Record an attempt
3
GET /api/games/{id}/review
Latest stored review
4
POST /api/games/{id}/review/regenerate
Enqueue a new review
4
GET /api/stats/weaknesses
Ranked weaknesses by rate
5
GET /api/stats/trends
Per-category rate over time
6
GET /api/sessions/today, POST /api/sessions
Practice queue and sessions
6
10. Worker design
Win probability. Convert centipawns with the commonly used Lichess formula: win% = 50 + 50 * (2 / (1 + exp(-0.00368208 * cp)) - 1). Mate scores map to 100 or 0. Classify by win-percentage loss. Starting thresholds, all tunable in winprob.py: inaccuracy 5 points, mistake 10, blunder 15. Skip classification for the first moves while the position is in opening theory (default: ply 1-10, or while the move appears in the ECO dataset once Phase 5 adds it).
Engine settings. Depth 12-14 and multi-PV 3 per position is the default. Store the settings on analysis_runs. Re-running with new settings creates a new run, never an overwrite.
Mistake types (Phase 5; heuristics using python-chess, each returns tags and the first matching type in priority order):
1. hanging_piece: after the user's move, a user piece is attacked and undefended (or attacked by a lower-value piece) and the opponent's best reply wins material.
2. missed_mate and missed_check: the best move gives mate or a decisive check.
3. missed_capture: the best move wins material by capture and the user played a non-capture.
4. missed_fork, missed_pin, missed_skewer: after the best move, one piece attacks two or more valuable targets, or pins or skewers.
5. ignored_threat: the opponent's previous move created a threat against an undefended piece and the user did not address it.
6. back_rank: mating pattern against a king boxed in on its back rank.
7. conversion: the user's win probability before the move was above 75% and fell below 55%.
8. time_pressure (tag): clock under 30 seconds or under 10% of the base time.
9. opening_error: out of theory with a loss of 10 or more points within the first 12 moves.
10. other: fallback.
Puzzle quality filters (puzzles.py):
• Starting position is the position before the user's mistake, with the user to move.
• Best move beats the second-best by at least 15 win-percentage points, so the solution is effectively unique.
• Skip positions already decided: win probability before outside the 20-90 range.
• Default solution length is 1-3 user moves. Longer lines need an explicit theme tag.
• Include missed opportunities (the opponent blundered and the user did not punish).
• Deduplicate by FEN. Store the full engine line so the UI can show the refutation.
• Spot-check a sample of generated puzzles after every generator change.
Review pipeline (facts.py, llm.py, review.py):
• Facts package (JSON): result, color, ratings, opening, time control, per-phase mistake counts, and the top 3-5 mistakes each with ply, SAN played, best SAN, FEN before, type, win-percentage loss and clock.
• Request: POST /api/chat to Ollama with stream: false, a JSON-schema format, low temperature (about 0.3), and thinking disabled for qwen3 (verify the current request field). Use keep_alive so the model stays loaded between games.
• Output schema: summary, result_explanation, key_moments[] (ply, san, what_happened, better_move, lesson), strengths[], habit_to_fix, practice_suggestion.
• Validation: every san and ply in key_moments must exist in the facts package, text length limits apply, and no engine evaluations may appear that are not in the facts. On failure retry up to 2 times, then store with validation_status = flagged.
• Resource note: on a 24 GB machine, run analysis and LLM jobs sequentially rather than at the same time.
11. Frontend
Routes: / (Status), /games, /games/:id, /train, /weaknesses, /sessions, /settings.
Key components: Board (react-chessboard with chess.js), MoveList (SAN with clock and classification badges), EvalChart (win probability per ply), ReviewPanel, PuzzleBoard (move entry, hint, retry, refutation display), JobProgress (polls /api/jobs/summary).
Conventions: server state through TanStack Query only, polling intervals defined in one place, all API types in src/types mirrored from the DTOs, Vite proxies /api to api:8080 in dev.
12. Phases
Each phase is complete only when its acceptance checks pass and the app runs end to end from docker compose up.
Phase 0: Walking skeleton
• Build: repo scaffold and Makefile; Compose with postgres, api, worker, web; Flyway V1 creating users and service_heartbeats; API with actuator and /api/status; worker loop that writes a heartbeat every few seconds and checks Ollama reachability; Status page showing all four services and Ollama.
• Demo: open the web app and see every service green, with last-heartbeat age for the worker.
• Acceptance: cold docker compose up --build works from a clean checkout; migrations apply on an empty DB; make test and make lint pass; .env.example is complete.
Phase 1: Game library
• Build: sync feature (chess.com archives client: set a User-Agent, fetch archives sequentially, respect rate limits); games migration; PGN upload; list with filters; game viewer that replays the stored PGN client-side with chess.js; ECO and opening name taken from PGN headers.
• Demo: enter a username, watch games appear, open one and step through it on the board.
• Acceptance: re-sync adds only new games; malformed or empty months are handled; a PGN with clock comments loads; Testcontainers tests cover sync and idempotency using fixture JSON (no live network in tests).
Phase 2: Engine analysis and mistake flagging
• Build: analysis_jobs, moves, analysis_runs, move_evals, mistakes migrations; worker claim loop with reaper and retries; Stockfish wrapper; analysis pipeline; win-probability and severity classification; sync now enqueues one job per new game; UI shows job progress, an eval chart, and mistakes highlighted on the board and move list.
• Demo: sync, watch progress, open an analyzed game and see where the blunders were.
• Acceptance: a full account analyzes unattended; killing the worker mid-game and restarting resumes cleanly with no duplicate rows; fixture games produce the expected classifications in fixtures/expected/; clock data appears on moves.
Phase 3: Puzzles from your mistakes
• Build: puzzles and puzzle_attempts migrations; generate_puzzles job with the quality filters; /api/puzzles/next and attempts endpoint; Train page with move entry, hint, retry and refutation display.
• Demo: solve puzzles drawn from your own games.
• Acceptance: every puzzle has a clear unique solution by the filters; attempts persist; no puzzle comes from a decided position.
Phase 4: Local LLM game reviews
• Build: game_reviews migration; facts builder; Ollama client; schema validation and retry; review_game job; ReviewPanel with a regenerate button and a model/prompt version tag.
• Demo: open any analyzed game and read its review.
• Acceptance: every analyzed game has a stored review; changing OLLAMA_MODEL needs no code change; a deliberately corrupted LLM output is rejected by validation in a test.
Phase 5: Level-aware weakness profile
• Build: classify.py with the mistake types above; ECO dataset import; phase and time-pressure tagging; weakness aggregation by rate (mistakes per 100 moves) in stats; Weaknesses page; puzzle filter by type; optional Maia comparison to flag mistakes typical for the 1100 band; regenerate reviews with the richer facts (new prompt version).
• Demo: a ranked list of your top weaknesses, each linking to its puzzles.
• Acceptance: top-3 weaknesses are stable across a re-run; rates, not counts, drive the ranking; Maia is skipped cleanly if unavailable. Risk: running lc0 and Maia in an arm64 Linux container needs verifying, so treat Maia as optional.
Phase 6: Deliberate practice loop
• Build: review_schedule; Leitner-box scheduling in Kotlin (FSRS optional later); "20 minutes on my top 3 weaknesses" sessions; difficulty calibration toward 70-80% success; timed drills for time-pressure mistakes; trend view of per-category rate in new games.
• Demo: a daily queue and a session summary.
• Acceptance: failed puzzles return sooner than solved ones; session composition follows the weakness ranking; the trend chart answers whether a specific weakness is improving.
Phase 7: Plug-and-play for other people
• Build: Spring Security with simple local accounts; user_id filtering on every query; onboarding flow (username, waiting screen, dashboard); fair job scheduling across users; per-user rating-band calibration.
• Acceptance: a second user onboards with no manual steps; user A can never read user B's data (covered by tests).
Phase 8: Extensions
Lichess puzzle supplementation by theme and rating band; opening explorer filtered to roughly 1000-1400 rated games; Lichess account import; LLM-written puzzle explanations; export and backups; GPL packaging review.
13. Testing strategy
• API: Testcontainers Postgres, one base test class, fixtures for chess.com JSON. No live network.
• Worker: pytest with fixture PGNs and low-depth Stockfish for determinism; unit tests for winprob, classify and puzzle filters; LLM tests use recorded and deliberately broken outputs.
• Web: Vitest and Testing Library for components and hooks.
• End to end: a smoke script that runs the full pipeline on a three-game fixture and asserts a review exists.
14. Conventions
• Naming: snake_case in SQL and Python, camelCase in Kotlin and TypeScript, kebab-case for migration file descriptions (V3__add-puzzles.sql).
• Config: only through environment variables and application.yml / config.py. No secrets in git.
• Errors: API returns a consistent error body; worker records last_error on jobs and never crashes the loop.
• Logging: structured, one line per job transition, with job id and game id.
• Commits: small, one logical change each, referencing the phase (for example phase-2: add stockfish wrapper).
15. Agent working agreement (copy into AGENTS.md)
1. Read docs/PLAN.md before starting. Work on exactly one phase at a time and do not build ahead.
2. Respect the decisions in section 3. If a task seems to require breaking one, stop and write an ADR instead of working around it.
3. Only Flyway migrations in api/ change the schema. Never edit an applied migration; add a new one.
4. The worker's SQL lives in worker/src/worker/db.py only.
5. Do not invent chess facts. Evaluations, best moves and mistake types come from the engine pipeline, and the LLM only phrases them.
6. Write tests with each change and use fixtures, not the live chess.com API.
7. Before reporting a phase done, verify: cold docker compose up --build works, tests and lint pass, the acceptance list for the phase is satisfied, and the README documents how to demo it.
8. When something says verify (library versions, Ollama request fields, Stockfish packaging), check the current official documentation and note what you found.
9. Ask before adding any dependency, service or table not in this plan.
16. Risks and open questions
• chess.com terms and rate limits: read the terms before opening the app to others.
• Puzzle quality: it makes or breaks training value; keep the spot-check routine.
• LLM hallucination: the validation step in Phase 4 is mandatory.
• Maia on arm64 containers: unverified; optional by design.
• Open decisions: Postgres versus MySQL is currently Postgres (JSONB, partial indexes, FILTER); revisit only with a concrete reason. Boot major version and exact starter names to be confirmed at project generation.
17. Glossary
FEN: text snapshot of a position. SAN: move notation like Nf3. UCI: the protocol used to talk to Stockfish. PV: principal variation, the engine's best line. Multi-PV: asking the engine for several best lines. ECO: opening classification codes. Win-percentage loss: drop in the mover's winning chances caused by a move. Missed opportunity: an opponent error the user failed to punish.