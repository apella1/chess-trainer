# Phase 10: Guided first-value onboarding

Lead a new player from registration directly through game import and initial analysis to their very first AI game review and personalized puzzle in under two minutes.

## Deliverables

- Interactive Onboarding Wizard modal and stepped walkthrough triggered upon first login.
- Real-time sync and analysis progress tracker with clear stage updates (fetching archives -> running Stockfish -> generating review).
- Instant First Value: Automatic redirection to the player's most instructive analyzed game with highlighted blunder.
- First Training Recommendation: Immediate prompt to solve the first generated puzzle from that game.
- Graceful empty states with helpful guidance when an account has no recent games or no qualifying blunders (including sample game demo fallback).
- Contextual explainer bridging game evidence, weakness classification, and practice recommendations.

## Demo

Sign up as a new user, enter a Chess.com username, follow the guided progress bar, view your first analyzed game review, and solve your first personal puzzle without ever hitting an empty screen.

## Acceptance checks

- A new user reaches their first actionable coaching result (review and puzzle) seamlessly from sign-up.
- Loading states provide clear progress indicators and realistic time estimates.
- Accounts with zero games or low game counts receive constructive guidance and an option to load sample games.
- No dead ends or empty dashboards during the onboarding experience.
