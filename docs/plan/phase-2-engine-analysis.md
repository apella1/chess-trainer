# Phase 2: Engine analysis and mistake flagging

## Deliverables

- Migrations for `analysis_jobs`, `moves`, `analysis_runs`, `move_evals`, and `mistakes`.
- Worker claim loop with reaper and retries.
- Stockfish wrapper and per-game analysis pipeline.
- Win-probability and severity classification.
- Sync enqueues one analysis job per new game.
- UI job progress, evaluation chart, and mistakes highlighted on the board and move list.

## Demo

Sync games, watch analysis progress, and open an analyzed game to see where blunders occurred.

## Acceptance checks

- A full account analyzes unattended.
- Killing the worker mid-game and restarting resumes cleanly with no duplicate rows.
- Fixture games produce expected classifications in `fixtures/expected/`.
- Clock data appears on moves.
