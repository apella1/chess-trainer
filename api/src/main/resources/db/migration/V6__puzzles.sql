-- V6: puzzles and puzzle_attempts tables
-- Puzzles are generated from the user's own mistakes by the worker.
-- Each puzzle has a unique solution (best move beats second-best by 15+ win% points).

CREATE TABLE puzzles (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID        REFERENCES users(id) ON DELETE CASCADE,
    source            TEXT        NOT NULL DEFAULT 'own_game',
    source_mistake_id UUID        REFERENCES mistakes(id) ON DELETE SET NULL,
    fen               TEXT        NOT NULL,
    side_to_move      TEXT        NOT NULL,
    solution_uci      TEXT[]      NOT NULL DEFAULT '{}',
    themes            TEXT[]      NOT NULL DEFAULT '{}',
    difficulty_est    NUMERIC(3,2),
    active            BOOLEAN     NOT NULL DEFAULT true,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_puzzles_user_active ON puzzles (user_id, active);

CREATE TABLE puzzle_attempts (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    puzzle_id     UUID        NOT NULL REFERENCES puzzles(id) ON DELETE CASCADE,
    user_id       UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    solved        BOOLEAN     NOT NULL,
    moves_tried   JSONB       NOT NULL DEFAULT '[]',
    time_ms       INTEGER,
    hints_used    INTEGER     NOT NULL DEFAULT 0,
    attempted_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_attempts_puzzle ON puzzle_attempts (puzzle_id);
CREATE INDEX idx_attempts_user ON puzzle_attempts (user_id, attempted_at DESC);
