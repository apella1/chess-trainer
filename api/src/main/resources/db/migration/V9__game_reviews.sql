-- V9: game_reviews table
-- Stores LLM-generated game reviews. Unique on (game_id, model, prompt_version)
-- so reviews can be regenerated and compared without losing history.

CREATE TABLE game_reviews (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id          UUID        NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    run_id           UUID        REFERENCES analysis_runs(id) ON DELETE SET NULL,
    model            TEXT        NOT NULL,
    prompt_version   TEXT        NOT NULL DEFAULT 'v1',
    facts_json       JSONB       NOT NULL,
    review_json      JSONB,
    review_text      TEXT,
    validation_status TEXT       NOT NULL DEFAULT 'ok',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (game_id, model, prompt_version)
);

CREATE INDEX idx_reviews_game ON game_reviews (game_id);
