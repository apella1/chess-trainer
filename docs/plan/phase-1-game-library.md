# Phase 1: Game library

## Deliverables

- Sync feature with a chess.com archives client that sets a User-Agent, fetches archives sequentially, and respects rate limits.
- Games migration.
- PGN upload.
- Games list with filters.
- Game viewer that replays stored PGNs client-side with chess.js.
- ECO and opening name taken from PGN headers.

## Demo

Enter a username, watch games appear, open a game, and step through it on the board.

## Acceptance checks

- Re-sync adds only new games.
- Malformed or empty months are handled.
- A PGN with clock comments loads.
- Testcontainers tests cover sync and idempotency using fixture JSON; tests make no live network calls.
