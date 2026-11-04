# ADR 0001: Monorepo

## Status
Accepted

## Context
The project has three distinct runtimes: a Spring Boot API, a Python worker, and a React
frontend. They could each live in their own repository.

## Decision
All three services live in a single repository with one `docker-compose.yml` at the root.

## Rationale
- A single `docker compose up --build` starts the entire app from a clean checkout. This
  dramatically reduces onboarding friction and the number of things that can go wrong in a
  development environment.
- Cross-cutting changes (e.g. adding a database column, a new job kind, and the UI that
  displays it) land in a single commit with a single PR. There is no inter-repo version
  coordination.
- The services are tightly coupled by design: the worker reads jobs that the API writes;
  the UI polls endpoints that reflect the worker's output. A monorepo makes this coupling
  explicit and manageable.
- The project is personal/small-team. The overhead of inter-repo management is not
  justified.

## Consequences
- The repo is larger and contains multiple languages. IDEs and tooling need to support
  both Kotlin/Gradle and Python/uv.
- A change to the API and a change to the worker land in the same commit history, which
  is a minor annoyance if you want to bisect one service in isolation.
