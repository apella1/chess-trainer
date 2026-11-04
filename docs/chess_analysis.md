# Chess Analysis

## Overview

The worker uses Stockfish to evaluate every position in a game and classifies each move.
The goal is not to produce grandmaster-level commentary but to identify the types of mistakes
that cost rating points at the 1100 level.

## Engine Settings

| Setting    | Default | Notes                                        |
|------------|---------|----------------------------------------------|
| Depth      | 14      | Per position. Lower is faster, higher is more accurate. Tunable via `ANALYSIS_DEPTH` env var. |
| Multi-PV   | 3       | Number of candidate lines. Needed to compute `second_best_eval_cp` for puzzle quality filters. Tunable via `ANALYSIS_MULTIPV`. |

Engine name and version are read from the UCI `id name` response on startup and stored on
every `analysis_runs` row. This means analysis output is always traceable to the exact engine
version that produced it.

## Win Probability Conversion

Centipawns are converted to win probability using the Lichess formula:

```
win% = 50 + 50 × (2 / (1 + exp(-0.00368208 × cp)) - 1)
```

Mate scores map to 100 (forced win) or 0 (forced loss).

**Why win probability instead of centipawns?**
Centipawns are not linear at high values. A swing from +0.5 to +2.0 is very significant, but
a swing from +8.0 to +9.5 is noise — the game is already decided either way. Win probability
compresses extreme values and gives a human-readable scale (0–100) that maps naturally to
"how much did this move hurt your chances?"

## Move Classification

Classifications are based on win-probability loss (the drop in win% caused by the move).
All thresholds are defined in `winprob.py` and are tunable.

| Classification | Win% loss threshold |
|----------------|---------------------|
| book           | Opening theory; not classified |
| best           | 0–2                 |
| good           | 2–5                 |
| inaccuracy     | 5–10                |
| mistake        | 10–15               |
| blunder        | ≥ 15                |

The first moves are skipped while the position is in opening theory (default: plies 1–10,
or while the move appears in the ECO dataset once Phase 5 adds it).

## Evaluations from the Mover's Perspective

All centipawn and win-probability values are stored from the point of view of the player who
is about to move. Positive = good for the mover. This is consistent with how Stockfish
reports evaluations when you flip the board perspective.

This means:
- `eval_before_cp = +1.0` means the mover has a slight edge before their move.
- `eval_after_cp = -0.5` means after the move, the opponent (now the mover) has the edge.
- `win_pct_loss` = `win_pct_before` - `win_pct_after` (positive means the move lost winning chances).

Never mix mover-perspective values with White-perspective values in the same query or
display.

## Mistake Types

Classified in Phase 5. Priority order: the first matching type is used.

1. **hanging_piece** — After the user's move, a user piece is attacked and undefended (or
   attacked by a lower-value piece) and the opponent's best reply wins material.
2. **missed_mate** — The best move delivers checkmate.
3. **missed_check** — The best move delivers a decisive check that the user missed.
4. **missed_capture** — The best move wins material by capture; the user played a non-capture.
5. **missed_fork** — After the best move, one piece attacks two or more valuable targets.
6. **missed_pin** — After the best move, a piece is pinned.
7. **missed_skewer** — After the best move, a more valuable piece is behind a less valuable one.
8. **ignored_threat** — The opponent's previous move created a threat the user did not address.
9. **back_rank** — Mating pattern against a king boxed in on its back rank.
10. **conversion** — Win probability was > 75% before the move and dropped below 55%.
11. **opening_error** — Out of theory with a loss of ≥ 10 points within the first 12 moves.
12. **other** — Fallback for any blunder not matching the above.

**Tags** (orthogonal to type):
- `time_pressure` — Clock under 30 seconds or under 10% of the base time when the move was played.

**Phases:**
- `opening` — before move 12 (or while in book)
- `middlegame` — moves 12–35 approximately
- `endgame` — after material drops below a threshold (determined by piece count)

## Only the User's Moves Are Mistakes

The opponent's blunders are not classified as mistakes. Instead, they become
`missed_opportunity` rows in `mistakes` when the user failed to punish them. This keeps the
weakness profile focused on the user's own patterns.

## Puzzle Quality Filters

A mistake qualifies as a puzzle if:

1. The best move beats the second-best by at least 15 win-percentage points (solution is
   effectively unique — there is one right answer).
2. The position is not already decided: `win_pct_before` is between 20 and 90.
3. Default solution length is 1–3 user moves. Longer lines need an explicit theme tag.
4. The FEN has not already been used for another puzzle (deduplication by starting position).

Missed opportunities (opponent blundered, user did not punish) are also included as puzzles.

## Analysis Pipeline per Game

```
1. Parse PGN with python-chess
2. Create analysis_runs row
3. For each position:
   a. Ask Stockfish for depth-14, multi-PV 3 evaluation
   b. Write moves row (san, uci, fen, clock)
   c. Write move_evals row (cp, mate, win%, classification)
4. Classify mistakes, write mistakes rows
5. Enqueue generate_puzzles job
6. Enqueue review_game job
```

## Stockfish in the Container

Stockfish is installed in the worker Docker image via the distro package manager or a
downloaded arm64 release. The exact binary path is set via the `STOCKFISH_PATH` environment
variable (default `/usr/games/stockfish` on Debian-based images).

On startup, the worker reads the engine name and version from the UCI `id name` line and
records it on every `analysis_runs` row.
