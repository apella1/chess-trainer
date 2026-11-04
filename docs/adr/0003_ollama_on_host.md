# ADR 0003: Ollama Runs on the Host

## Status
Accepted

## Context
The review pipeline requires a local LLM for generating game reviews. The LLM could be run:
- Inside a Docker container
- As a native process on the host machine, accessible from containers

## Decision
Ollama runs natively on the host. Containers reach it at `http://host.docker.internal:11434`.

## Rationale
- **GPU access on macOS.** Docker on macOS runs containers inside a Linux VM. That VM cannot
  access the Apple Silicon GPU or Neural Engine. Running Ollama natively gives it full access,
  which means inference is 3–10x faster than CPU-only.
- **Simplicity.** Ollama is a single binary installed with `brew install ollama`. It manages
  model downloads and serves a REST API. No Docker configuration needed.
- **Model persistence.** Models downloaded by Ollama persist across `docker compose down`.
  If Ollama were containerized, model storage would need a volume or re-download on each
  container start.

## Consequences
- Ollama must be installed and running on the host before the worker can generate reviews.
  The worker checks reachability at startup and reports it in the heartbeat.
- If Ollama is not available, `review_game` jobs fail and are retried. Analysis and puzzle
  generation are not affected.
- In a Linux production environment (e.g. a server with an NVIDIA GPU), Ollama can be
  containerized. The `OLLAMA_URL` environment variable makes this a config change, not a
  code change.
