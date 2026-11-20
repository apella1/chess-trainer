# Phase 12: Extensions and ecosystem integrations

Expand platform capabilities with supplementary puzzle databases, opening exploration, cross-platform import, and automated data management.

## Deliverables

- Lichess puzzle database integration to supplement rare mistake types and provide warmup drills.
- Rating-band opening explorer (filtered to 1000–1400 games) showing common amateur mistakes by opening variation.
- Lichess account synchronization alongside Chess.com.
- Interactive LLM puzzle explanations providing conversational hints and coaching commentary during drills.
- One-click account data export (PGNs, analysis, puzzle attempt history) and automated database backup tooling.
- Formal open-source licensing and packaging audit ensuring strict compliance with Stockfish and python-chess GPL-3.0 requirements.

## Demo

Sync games from both Chess.com and Lichess, explore common amateur pitfalls in the Sicilian Defense via the Opening Explorer, solve a supplementary Lichess puzzle when your local blunder queue is empty, and export your complete training archive to JSON/PGN.

## Acceptance checks

- Supplementary puzzles are clearly differentiated from personal blunder puzzles.
- Opening explorer aggregates stats exclusively within the target rating band.
- Lichess game import respects API terms and rate limits.
- Account export generates valid, downloadable PGN and JSON archives.
- Open-source distribution documentation complies with GPL-3.0.
