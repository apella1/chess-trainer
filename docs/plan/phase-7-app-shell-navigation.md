# Phase 7: Unified navigation and app shell

Unify the application experience with an intuitive, responsive app shell, seamless contextual navigation bridges between features, and live activity awareness.

## Deliverables

- Persistent responsive App Shell:
  - Collapsible sidebar on desktop, responsive slide-out drawer on mobile.
  - Active route highlights, badges for due review items, and keyboard navigation shortcuts.
- Global Activity Status ticker:
  - Persistent header indicator polling `/api/jobs/summary`.
  - Non-intrusive status pill indicating background game syncing, engine analysis progress, and review generation.
- Contextual navigation bridges ("The Coaching Loop"):
  - Game Detail -> "Train Mistakes from This Game" quick action button.
  - Review Panel -> "Practice Habit to Fix" direct link opening a targeted drill.
  - Weaknesses Page -> "Launch Targeted Session" CTA on each weakness card.
  - Train Page -> "Inspect Original Game Context" link navigating back to the game at the blunder move.
- Global Breadcrumbs supporting hierarchical location awareness (`Games > Blitz 5|3 vs Magnus > Move 24 Mistake > Practice`).
- Quick user switcher chip and local settings drawer (theme selector, sound effects toggle, board coordinates).

## Demo

Navigate across the application using the persistent shell, observe background analysis job activity in real time via the header pill, click "Train Mistakes" directly from an LLM game review, and seamlessly jump from a puzzle back to the original game position.

## Acceptance checks

- Every core page is accessible within 1 click from anywhere in the application.
- Active background analysis jobs display a persistent, non-intrusive indicator in the header without blocking user interaction.
- Users can navigate seamlessly between game analysis, weakness review, and puzzle training without losing context.
- Mobile layout adapts cleanly with an accessible slide-out navigation menu.
- Breadcrumb navigation allows single-click backtracking across nested views.
