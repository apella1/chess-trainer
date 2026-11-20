# Phase 6: Deliberate practice loop

## Deliverables

- 5-box Leitner spaced repetition engine (`review_schedule` table and service).
- Structured practice sessions ("20 minutes on top 3 weaknesses") recorded in `practice_sessions`.
- Dynamic difficulty calibration targeting a 70–80% puzzle success rate.
- Timed blunder drills with active countdown timers for `time_pressure` tagged mistakes.
- Historical trend tracking endpoint (`/api/stats/trends`) calculating error rates across sequential game batches.
- Sessions page featuring:
  - Daily review queue summary (due count, streak, box distribution).
  - Practice session launcher with weakness focus options.
  - Interactive trend charts visualizing whether specific weakness rates are falling.
  - Session history log showing completed sessions and solve accuracy.

## Demo

Launch a daily practice session from the Sessions page, solve scheduled puzzles where failed items return to Box 1 for immediate review, complete a timed drill, and view the updated trend chart tracking mistake rates over time.

## Acceptance checks

- Failed puzzles return to Box 1 for rapid re-review, while solved puzzles advance to longer review intervals.
- Session composition dynamically balances puzzles according to the player's top weakness rankings.
- Timed drills enforce strict per-puzzle time limits and persist response latency.
- The trend chart demonstrates whether a specific mistake type is declining over consecutive game batches.
