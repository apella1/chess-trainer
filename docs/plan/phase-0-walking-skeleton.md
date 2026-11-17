# Phase 0: Walking skeleton

## Deliverables

- Repository scaffold and Makefile.
- Docker Compose with Postgres, API, worker, and web services.
- Flyway V1 creating `users` and `service_heartbeats`.
- API actuator health and `/api/status`.
- Worker loop that writes a heartbeat every few seconds and checks Ollama reachability.
- Status page showing all four services and Ollama.

## Demo

Open the web app and see every service green, including the worker's last-heartbeat age.

## Acceptance checks

- A cold `docker compose up --build` works from a clean checkout.
- Migrations apply on an empty database.
- `make test` and `make lint` pass.
- `.env.example` is complete.
