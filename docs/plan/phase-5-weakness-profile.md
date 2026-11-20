# Phase 5: Level-aware weakness profile

## Deliverables

- `classify.py` with complete mistake heuristics tailored to the 1000–1400 rating band:
  - Hanging piece detection (undefended or underdefended pieces).
  - Missed tactics (forks, pins, skewers, missed checkmates, decisive captures).
  - Ignored opponent threats.
  - Conversion errors (positions with >75% win probability dropping below 55%).
  - Time-pressure tagging (moves made with <30 seconds or <10% clock remaining).
- ECO dataset integration to categorize opening variations and suppress false tactical flags during book moves.
- Game phase tagging (opening, middlegame, endgame) based on piece count and development.
- Weakness aggregation queries in API (`/api/stats/weaknesses`) calculating error rates normalized per 100 moves.
- Interactive Weaknesses page with ranked cards, frequency percentages, severity breakdown, and game phase filters.
- Direct puzzle drill-down: click any weakness card to immediately launch tactical training for that specific category.
- Optional Maia 1100 model comparison to highlight mistakes characteristic of the user's specific rating band.
- LLM game review regeneration incorporating rich classification tags and mistake context.

## Demo

Open the Weaknesses page to view your top recurring tactical flaws ranked by error rate per 100 moves, and click "Train Weakness" on any category to practice solving puzzles matching that mistake type.

## Acceptance checks

- Mistake rankings are strictly driven by error rates per 100 moves rather than raw counts.
- Opening moves conforming to ECO book theory are not classified as tactical blunders.
- Clicking any weakness card filters or launches training specifically targeting that mistake type.
- Maia comparison gracefully falls back without errors if lc0 or weights are not installed.
- Classification results are deterministic and idempotent across re-runs.

## Risk

Running lc0 and Maia in an arm64 Linux container requires specific binary compatibility; Stockfish heuristics provide full coverage so Maia remains an optional enhancement.
