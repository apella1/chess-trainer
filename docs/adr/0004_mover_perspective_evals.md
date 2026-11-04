# ADR 0004: Evaluations Stored from the Mover's Perspective

## Status
Accepted

## Context
Stockfish can report evaluations from White's perspective (positive = White is better) or
from the mover's perspective (positive = the side to move is better). The UI and analysis
code need to agree on which convention is used.

## Decision
All centipawn and win-probability values stored in `move_evals` are from the mover's
perspective. Positive means good for the side that is about to move. This convention is
never mixed with White-perspective values in the same table or query.

## Rationale
- **Natural mistake representation.** A move that hurts the player who made it always
  produces a positive `win_pct_loss` regardless of color. There are no sign-flip gymnastics
  in the analysis code.
- **Consistency with the win-probability formula.** The Lichess formula treats positive
  centipawns as good for the mover. Using the same convention end-to-end avoids silent
  bugs from sign mismatches.
- **Simpler classification logic.** "This move cost the user N win-percentage points" is
  directly readable from `win_pct_loss` without checking which color was moving.

## Consequences
- When the UI displays an evaluation chart, it must flip the sign for alternating plies if
  it wants a White-perspective chart (positive = White is better). The `EvalChart` component
  handles this transformation in the presentation layer only.
- Code comments and variable names must be explicit: `eval_before_cp` means
  "centipawns from the mover's perspective before this move."
- Any query that joins `move_evals` and filters by evaluation must be written with
  mover-perspective semantics.
