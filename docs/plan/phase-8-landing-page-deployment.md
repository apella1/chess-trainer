# Phase 8: Business-grade landing page and public deployment

Deliver a high-converting, professional public landing page and a production-ready, easily deployable packaging setup for public release.

## Deliverables

- Business-grade public landing page:
  - Hero section featuring a compelling value proposition, direct CTA ("Analyze My Games Free"), and an interactive demo puzzle widget playable right on the page without logging in.
  - "Why Tempo" value pillar cards: Level-aware mistake classification vs raw engine numbers, puzzles generated from your own games, local AI coach reviews, and evidence-based progress tracking.
  - Interactive feature showcase with tabbed previews of Game Replay, Eval Charts, and AI Review summaries.
  - Social proof and target player archetypes (specifically tuned for 1000–1400 rapid players on Chess.com).
  - Professional footer with GitHub repo link, documentation index, GPL-3.0 licensing notices for Stockfish and python-chess, and privacy disclosures.
- Layout routing split:
  - Unauthenticated visitors land on the public landing page with interactive demo capabilities.
  - Active users transition seamlessly into the authenticated App Shell.
- Production deployment configuration:
  - Multi-stage production `Dockerfile` for `web` serving pre-built static assets via optimized Nginx with gzip/brotli compression and security headers.
  - Production Compose manifest (`docker-compose.prod.yml`) with environment variable validation, healthcheck policies, and restart strategies.
  - Nginx reverse-proxy configuration routing `/api/*` to the Spring Boot backend with connection pooling and rate limiting.
  - Production deployment guide and one-step startup script (`scripts/deploy.sh`).

## Demo

Open the root URL in an incognito window to view the commercial-grade landing page, solve an interactive demo puzzle, click "Get Started" to enter the app, and run `docker compose -f docker-compose.prod.yml up` to verify production container builds and asset serving.

## Acceptance checks

- Public landing page achieves high visual polish and full responsiveness across mobile, tablet, and desktop viewports.
- Unauthenticated visitors can experience product value through interactive demo components without backend database errors.
- Production Nginx container serves compressed static assets with appropriate caching and security headers.
- Single command deployment starts all services with production configuration and passing healthchecks.
- Stockfish and python-chess GPL-3.0 attribution and license terms are prominently displayed in the footer.
