# ADR 0002: Postgres as Job Queue

## Status
Accepted

## Context
The worker needs to receive work items (analyze a game, generate puzzles, write a review)
from the API. Options considered:
- A dedicated message broker (RabbitMQ, Redis Streams, AWS SQS)
- Postgres with `SELECT ... FOR UPDATE SKIP LOCKED`

## Decision
Use Postgres with `SELECT ... FOR UPDATE SKIP LOCKED` as the job queue.

## Rationale
- **No additional service.** Postgres is already required. Adding a broker adds another
  process to run, configure, monitor, and secure.
- **Transactional safety.** A worker can claim a job and write its first DB rows in a single
  transaction. If the transaction fails, the job is never marked as running and will be
  claimed again. This is impossible with a separate broker without two-phase commit.
- **Debuggability.** Job state is a row in a table. You can inspect it, update it, or
  replay it with plain SQL. No broker-specific tooling required.
- **Sufficient throughput.** This application processes at most a few hundred games per user.
  Postgres can handle this load without any tuning. The `SKIP LOCKED` pattern is well-tested
  at much higher throughput.
- **Reaper simplicity.** Stale jobs (worker died mid-run) are reset by a SQL UPDATE. No
  broker acknowledgement protocol needed.

## Consequences
- The jobs table grows over time. A periodic cleanup job should archive or delete completed
  rows older than N days.
- If the job volume grows by orders of magnitude (e.g. serving thousands of users with
  real-time analysis), revisit with a proper broker. The job abstraction in `jobs.py` is
  designed to make this migration straightforward.
