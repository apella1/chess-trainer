# Phase 10: Evidence-based improvement loop

Close the product loop by connecting deliberate practice to later real-game outcomes. This
extends Phase 6's trend view with a trustworthy baseline, enough context to interpret change,
and a concrete next training priority.

## Deliverables

- A per-weakness baseline and subsequent comparison using the player's own analyzed moves, normalized as mistakes per 100 moves.
- Progress views that include the period, analyzed game/move counts, and other context needed to interpret sparse or changing samples.
- A clear insufficient-data state; do not imply improvement or decline when there is not enough comparable game evidence.
- A comparison of puzzle practice results and later real-game error rates for the practiced weakness.
- Updated training priorities that use both recent game mistakes and practice results.
- A concise progress summary that distinguishes observed change from a causal claim about practice.

## Demo

Complete targeted practice, import and analyze later games, then see a comparison with the
baseline, the amount of evidence behind it, and an updated recommendation for what to practice
next.

## Acceptance checks

- Error rates use analyzed moves as the denominator, not raw mistake counts.
- Comparisons show their time window and sample size and do not claim a trend when evidence is insufficient.
- Practice recommendations respond to both puzzle outcomes and later game performance.
- The player can answer which weakness is improving, which still needs work, and what to practice next.
- Reports do not state that practice caused an observed change; they present the evidence and its limits.
