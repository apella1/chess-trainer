# LLM Game Reviews

## Purpose

After a game is analyzed, the worker generates a written review using a local LLM via Ollama.
The review turns dry engine numbers into plain-English coaching feedback tailored to a ~1100
rated player.

## Why a Local LLM

- No data leaves the machine. Chess games are personal.
- No API costs or rate limits.
- The model can stay loaded between games using Ollama's `keep_alive` parameter, making
  batch processing fast.
- If the model is unavailable or produces invalid output, the review is stored with
  `validation_status = flagged` rather than crashing the pipeline. Analysis and puzzles
  are not blocked by review generation.

## Model

Default: `qwen3:8b`  
Fallback: `llama3.1:8b`  
Configurable via `OLLAMA_MODEL` environment variable. No code change needed to switch models.

For qwen3, thinking mode is disabled (set `thinking: false` in the request). Verify the
current Ollama request field name against official docs if this changes.

## The LLM Never Computes Chess Facts

The worker builds a structured facts package from Stockfish output and passes it to the LLM.
The LLM receives only:
- Game result, player colors, ratings, opening name, time control
- Per-phase mistake counts
- The top 3–5 mistakes, each with: ply, SAN played, best SAN, FEN before, mistake type,
  win-percentage loss, and clock remaining

The LLM writes prose. It does not compute evaluations, find best moves, or invent chess
variations. Its output is validated against the facts it received.

## Request Parameters

```json
{
  "model": "qwen3:8b",
  "messages": [{ "role": "user", "content": "..." }],
  "stream": false,
  "format": { ... },
  "options": { "temperature": 0.3 },
  "keep_alive": "10m",
  "think": false
}
```

Temperature is kept low (≈ 0.3) for consistent, factual output.

## Output Schema

The LLM is asked to return structured JSON:

```json
{
  "summary": "string (2-3 sentences overview)",
  "result_explanation": "string (why the game was won/lost/drawn)",
  "key_moments": [
    {
      "ply": 23,
      "san": "Nd4",
      "what_happened": "string",
      "better_move": "Nf4",
      "lesson": "string"
    }
  ],
  "strengths": ["string"],
  "habit_to_fix": "string (single most important habit)",
  "practice_suggestion": "string"
}
```

## Validation Rules

After receiving the LLM response:

1. Every `ply` in `key_moments` must exist in the facts package.
2. Every `san` and `better_move` in `key_moments` must match the facts package values
   for that ply.
3. Text length limits: `summary` ≤ 500 chars, each `lesson` ≤ 300 chars.
4. No engine evaluation numbers (centipawns or percentages) may appear in the text that are
   not present in the facts package. This prevents hallucinated evaluations.
5. `key_moments` must have between 1 and 5 entries.

On validation failure: retry up to 2 times. After 3 total failures, store the review with
`validation_status = flagged` and the raw output in `review_json`. Do not block the pipeline.

## Prompt Versioning

The `REVIEW_PROMPT_VERSION` environment variable (default `v1`) is stored on every
`game_reviews` row alongside the model name. This means:
- Changing the prompt creates new reviews without deleting old ones.
- You can compare output across prompt versions for the same game.
- The regenerate endpoint (`POST /api/games/{id}/review/regenerate`) enqueues a new job that
  will produce a new `game_reviews` row under the current prompt version.

## Ollama Connectivity

Ollama runs on the host machine, not in Docker. Containers reach it at:
`http://host.docker.internal:11434`

This is because Docker on macOS cannot use the Apple GPU. Running Ollama natively gives it
full access to Apple Silicon's GPU/Neural Engine.

The worker checks Ollama reachability on startup and reports it in the heartbeat `details`
field, which appears on the Status page.
