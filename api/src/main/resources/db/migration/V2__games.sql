-- V2: games table
-- Stores imported games from chess.com sync and PGN upload.
-- Unique on (user_id, source, external_id) so re-syncing never duplicates.

CREATE TABLE games (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID        NOT NULL REFERENCES users(id),
    source           TEXT        NOT NULL DEFAULT 'chesscom',
    external_id      TEXT        NOT NULL,
    url              TEXT,
    pgn              TEXT        NOT NULL,
    played_at        TIMESTAMPTZ,
    time_class       TEXT,
    time_control     TEXT,
    user_color       TEXT,
    result           TEXT,
    termination      TEXT,
    user_rating      INTEGER,
    opp_rating       INTEGER,
    opp_username     TEXT,
    eco              TEXT,
    opening_name     TEXT,
    analysis_status  TEXT        NOT NULL DEFAULT 'none',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, source, external_id)
);

CREATE INDEX idx_games_user_played ON games (user_id, played_at DESC);
CREATE INDEX idx_games_user_result ON games (user_id, result);
CREATE INDEX idx_games_user_color  ON games (user_id, user_color);
CREATE INDEX idx_games_time_class  ON games (user_id, time_class);
