# Phase 9: Guided first-value onboarding

Make the existing username-only onboarding lead a new player from account creation to their
first useful coaching experience, not just to an empty dashboard.

## Deliverables

- A guided path from username entry through game import, analysis progress, and the first completed game review.
- Clear next steps while games are syncing or analyzing, including understandable recovery paths when a step fails.
- A first training recommendation linked to an analyzed mistake and a playable puzzle when a qualifying puzzle exists.
- Useful empty states when the account has no importable games or analysis has not produced a qualifying mistake yet.
- A short explanation of how game evidence, weakness rankings, and practice recommendations relate.

## Demo

Create a new account with a username, follow the import and analysis progress, then reach a game review and a relevant training activity without manual setup.

## Acceptance checks

- A new user can reach a meaningful first coaching result using only the chess.com username and the planned local services.
- The flow never presents an empty or stalled state without explaining what is happening and what the user can do next.
- A user with no importable games or no qualifying puzzle receives an accurate explanation and a useful next step rather than fabricated coaching content.
- The first recommended activity links to real imported game and engine-analysis evidence.
