# Phase 3: Puzzles from your mistakes

## Deliverables

- Migrations for `puzzles` and `puzzle_attempts`.
- `generate_puzzles` job using the quality filters in [the shared worker design](../plan.md).
- `/api/puzzles/next` and puzzle-attempts endpoint.
- Train page with move entry, hint, retry, and refutation display.

## Demo

Solve puzzles drawn from your own games.

## Acceptance checks

- Every puzzle has a clear, unique solution according to the filters.
- Attempts persist.
- No puzzle comes from a decided position.
