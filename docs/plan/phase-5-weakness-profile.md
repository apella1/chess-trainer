# Phase 5: Level-aware weakness profile

## Deliverables

- `classify.py` with the mistake types described in [the shared worker design](../plan.md).
- ECO dataset import.
- Phase and time-pressure tagging.
- Weakness aggregation by rate (mistakes per 100 moves) in stats.
- Weaknesses page.
- Puzzle filter by type.
- Optional Maia comparison to flag mistakes typical for the 1100 band.
- Regenerated reviews with richer facts and a new prompt version.

## Demo

Show a ranked list of top weaknesses, each linking to its puzzles.

## Acceptance checks

- Top-three weaknesses are stable across a re-run.
- Rates, not counts, drive the ranking.
- Maia is skipped cleanly if unavailable.

## Risk

Running lc0 and Maia in an arm64 Linux container needs verification, so Maia remains optional.
