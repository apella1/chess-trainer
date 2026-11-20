"""
Ollama LLM client for game reviews.

Design principles:
- Low temperature (0.3) for consistent, factual output
- Structured JSON output enforced via Ollama's format field
- Validation: every ply and SAN in key_moments must exist in the facts package
- On validation failure: retry up to 2 times, then store with flagged status
- The LLM never computes chess facts — it only phrases them
"""

import json
import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from worker.config import settings

log = logging.getLogger(__name__)

# Output schema the LLM must follow
REVIEW_SCHEMA = {
    "type": "object",
    "required": ["summary", "result_explanation", "key_moments", "strengths", "habit_to_fix", "practice_suggestion"],
    "properties": {
        "summary": {"type": "string"},
        "result_explanation": {"type": "string"},
        "key_moments": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["ply", "san", "what_happened", "better_move", "lesson"],
                "properties": {
                    "ply": {"type": "integer"},
                    "san": {"type": "string"},
                    "what_happened": {"type": "string"},
                    "better_move": {"type": "string"},
                    "lesson": {"type": "string"},
                },
            },
        },
        "strengths": {"type": "array", "items": {"type": "string"}},
        "habit_to_fix": {"type": "string"},
        "practice_suggestion": {"type": "string"},
    },
}

SYSTEM_PROMPT = """You are a chess coach writing a post-game review for a ~1100 rated player.
You will receive structured facts about the game. Write honest, encouraging feedback.
Focus on the 1-3 move tactical patterns that cost the most winning chances.
Do NOT invent evaluations or moves not in the facts. Use plain English, no chess jargon."""


def build_prompt(facts: dict[str, Any]) -> str:
    result = facts.get("result", "unknown")
    color = facts.get("user_color", "?")
    opp = facts.get("opp_username", "opponent")
    opening = facts.get("opening", {}).get("name") or "unknown opening"
    mistakes = facts.get("top_mistakes", [])
    phase_counts = facts.get("phase_mistake_counts", {})

    prompt = f"""Game facts:
- Result: {result} as {color} vs {opp}
- Ratings: {facts.get('user_rating')} vs {facts.get('opp_rating')}
- Opening: {opening} [{facts.get('opening', {}).get('eco', '')}]
- Time control: {facts.get('time_class')} ({facts.get('time_control')}s)
- Total moves: {facts.get('total_moves')}
- Mistakes by phase: opening={phase_counts.get('opening', 0)}, middlegame={phase_counts.get('middlegame', 0)}, endgame={phase_counts.get('endgame', 0)}

Key moments (worst mistakes):
"""
    for i, m in enumerate(mistakes[:3], 1):
        m_type = m.get('type', 'mistake').replace('_', ' ')
        prompt += f"{i}. Ply {m['ply']}: played {m['san']}, best was {m['best_uci']} (pattern: {m_type}, {m['win_pct_loss']}% win chance lost, {m['phase']})\n"

    prompt += "\nWrite a concise coaching review following the required JSON schema."
    return prompt


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def call_ollama(prompt: str) -> dict[str, Any]:
    """Call Ollama and return parsed JSON. Retries up to 3 times on network errors."""
    payload: dict[str, Any] = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "format": REVIEW_SCHEMA,
        "options": {"temperature": 0.3},
        "keep_alive": "10m",
    }

    # Disable thinking for qwen3 models
    if "qwen3" in settings.ollama_model.lower():
        payload["think"] = False

    response = httpx.post(
        f"{settings.ollama_url}/api/chat",
        json=payload,
        timeout=120.0,
    )
    response.raise_for_status()
    data = response.json()
    content = data["message"]["content"]
    return json.loads(content)


def validate_review(review: dict[str, Any], facts: dict[str, Any]) -> list[str]:
    """
    Validate the LLM output against the facts package.
    Returns a list of validation error messages (empty = valid).
    """
    errors = []
    facts_plies = {m["ply"] for m in facts.get("top_mistakes", [])}
    facts_sans = {m["san"] for m in facts.get("top_mistakes", [])}

    key_moments = review.get("key_moments", [])
    for km in key_moments:
        ply = km.get("ply")
        san = km.get("san")

        if ply not in facts_plies:
            errors.append(f"key_moment ply {ply} not in facts package")

        if san not in facts_sans:
            errors.append(f"key_moment san '{san}' not in facts package")

        # Text length limits
        if len(km.get("lesson", "")) > 400:
            errors.append(f"key_moment lesson at ply {ply} exceeds 400 chars")
        if len(km.get("what_happened", "")) > 400:
            errors.append(f"key_moment what_happened at ply {ply} exceeds 400 chars")

    if len(review.get("summary", "")) > 600:
        errors.append("summary exceeds 600 chars")

    if len(key_moments) > 5:
        errors.append(f"key_moments has {len(key_moments)} entries (max 5)")

    return errors


def generate_review(facts: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """
    Generate and validate a review for a game.

    Returns (review_json, validation_status) where validation_status is
    'ok' or 'flagged'.

    Retries validation up to 2 times before storing as flagged.
    """
    prompt = build_prompt(facts)
    last_review = {}
    last_errors: list[str] = []

    for attempt in range(3):
        try:
            review = call_ollama(prompt)
            errors = validate_review(review, facts)
            if not errors:
                return review, "ok"
            last_review = review
            last_errors = errors
            log.warning(
                "Review validation failed (attempt %d): %s",
                attempt + 1, "; ".join(errors),
            )
        except Exception as exc:
            log.error("Ollama call failed (attempt %d): %s", attempt + 1, exc)
            last_review = {}
            last_errors = [str(exc)]

    log.error("Review stored as flagged after 3 attempts: %s", "; ".join(last_errors))
    return last_review, "flagged"
