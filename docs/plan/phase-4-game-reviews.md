# Phase 4: Local LLM game reviews

## Deliverables

- `game_reviews` migration.
- Facts builder.
- Ollama client.
- Schema validation and retry.
- `review_game` job.
- ReviewPanel with a regenerate button and model/prompt version tag.

## Demo

Open any analyzed game and read its review.

## Acceptance checks

- Every analyzed game has a stored review.
- Changing `OLLAMA_MODEL` requires no code change.
- A test verifies that deliberately corrupted LLM output is rejected by validation.
