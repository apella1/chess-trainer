# Job Queue

## Why Postgres, Not a Message Broker

The job queue is implemented as a table in Postgres using `SELECT ... FOR UPDATE SKIP LOCKED`.
This avoids a dependency on Redis, RabbitMQ, or any external broker. The benefits for this
project are:

- **Simplicity.** One fewer service to run, configure, and debug.
- **Transactionality.** A worker can claim a job and write its first results in a single
  transaction. If the transaction rolls back, the job is never marked as running.
- **Debuggability.** Job state is visible in the database alongside the data it operates on.
  A simple `SELECT` shows everything.
- **Sufficient throughput.** This application analyzes chess games, not millions of events per
  second. Postgres can handle the job volume comfortably.

## Table: analysis_jobs

See `data_model.md` for the full schema. Key columns:

- `status`: `pending` → `running` → `done` | `failed`
- `locked_by`: the worker instance UUID that claimed the job
- `locked_at`: when the claim happened
- `attempts`: incremented on each claim
- `max_attempts`: default 3; after this many failures the job is not retried

## Claim Pattern

```sql
UPDATE analysis_jobs
SET    status    = 'running',
       locked_by = :instance_id,
       locked_at = now(),
       attempts  = attempts + 1,
       started_at = now()
WHERE  id = (
    SELECT id FROM analysis_jobs
    WHERE  status = 'pending'
      AND  attempts < max_attempts
    ORDER  BY created_at
    FOR UPDATE SKIP LOCKED
    LIMIT 1
)
RETURNING *;
```

`SKIP LOCKED` means concurrent workers each get their own job without contention or deadlocks.

## Reaper

The worker runs a reaper on startup and periodically (every 5 minutes). It resets jobs that
have been in `running` state for more than 15 minutes:

```sql
UPDATE analysis_jobs
SET    status    = 'pending',
       locked_by = null,
       locked_at = null
WHERE  status    = 'running'
  AND  locked_at < now() - interval '15 minutes';
```

This handles worker crashes without manual intervention.

## Retry Backoff

Failed jobs are retried with a growing delay:
- Attempt 1 → immediate retry
- Attempt 2 → retry after 5 minutes
- Attempt 3 → retry after 30 minutes
- After `max_attempts` → status stays `failed`; `last_error` records the exception

The delay is implemented by setting `created_at` to `now() + delay` when marking a job
as pending for retry. The claim query orders by `created_at`, so delayed jobs are skipped.

## Job Kinds

| Kind              | Enqueued by             | Does                                          |
|-------------------|-------------------------|-----------------------------------------------|
| analyze_game      | sync / PGN upload       | Runs Stockfish, writes moves, move_evals, mistakes |
| generate_puzzles  | analyze_game completion | Creates puzzles from qualifying mistakes      |
| review_game       | analyze_game completion | Builds facts package, calls Ollama, writes review |

## Idempotency

- Jobs check for existing work before writing. Re-running a completed job does not create
  duplicate rows.
- Analysis creates a new `analysis_runs` row, so re-running with different engine settings
  produces a new run rather than overwriting history.

## Resource Constraint

On a machine with 24 GB of RAM, Stockfish analysis and Ollama inference should not run
simultaneously. The worker processes `analyze_game` and `generate_puzzles` jobs first,
then processes `review_game` jobs in a separate pass. This is enforced by ordering the
job claim query by kind priority or by running separate worker modes.
