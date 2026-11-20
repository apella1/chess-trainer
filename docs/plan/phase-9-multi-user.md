# Phase 9: Multi-user authentication and tenant isolation

Transform the single-tenant workstation into a secure, multi-user platform where any visitor can register and train independently.

## Deliverables

- Spring Security integration with local user authentication (secure password hashing with BCrypt, JWT or session-based authentication).
- User registration and login endpoints with input validation.
- Tenant data isolation enforcing `user_id` scoping across all JPA queries, repositories, and worker jobs.
- Fair background job scheduling preventing one user's bulk sync from starving another user's single-game analysis.
- Per-user rating band calibration customizing mistake severity thresholds to the user's specific skill level.
- Auth UI: Login, registration, password management, and account profile settings modal.

## Demo

Register two distinct user accounts in separate browser sessions, import games in both, and verify that neither user can see or access the other's games, reviews, or practice history.

## Acceptance checks

- Unauthenticated requests to protected `/api/*` endpoints return 401 Unauthorized.
- Automated tests verify that User A cannot read or modify User B's games, moves, mistakes, or puzzles.
- Background worker processes jobs fairly across different user accounts without queue starvation.
- Password credentials are securely hashed and never exposed in logs or API responses.
