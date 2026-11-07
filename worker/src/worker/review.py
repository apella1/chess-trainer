"""
Review pipeline: builds facts, calls LLM, validates, stores.
"""

import logging
from typing import Any

from worker import db
from worker.config import settings
from worker.facts import build_facts
from worker.llm import generate_review

log = logging.getLogger(__name__)


def review_game(job: dict[str, Any]) -> None:
    """
    Generate a game review using the local LLM.

    Called by the main loop when a review_game job is claimed.
    The job payload contains:
    - game_id: UUID of the analyzed game to review
    """
    game_id = str(job["game_id"])

    # Skip if review already exists for this model/prompt version
    if db.review_exists(game_id, settings.ollama_model, settings.review_prompt_version):
        log.info("Review already exists for game %s, skipping", game_id)
        return

    log.info(
        "Generating review for game %s with model=%s prompt_version=%s",
        game_id, settings.ollama_model, settings.review_prompt_version,
    )

    # Build the facts package from engine analysis
    facts = build_facts(game_id)
    if not facts:
        raise ValueError(f"Could not build facts for game {game_id} — analysis may be incomplete")

    # Get the analysis run ID for the review record
    run_id = db.get_latest_analysis_run_id(game_id)

    # Call the LLM and validate the output
    review_json, validation_status = generate_review(facts)

    # Extract plain-text summary from the structured review
    review_text = review_json.get("summary", "") if review_json else ""

    # Store the review
    db.insert_review(
        game_id=game_id,
        run_id=run_id,
        model=settings.ollama_model,
        prompt_version=settings.review_prompt_version,
        facts_json=facts,
        review_json=review_json,
        review_text=review_text,
        validation_status=validation_status,
    )

    log.info(
        "Review stored for game %s: validation_status=%s",
        game_id, validation_status,
    )
