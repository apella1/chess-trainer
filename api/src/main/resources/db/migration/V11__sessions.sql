-- V11: review_schedule and practice_sessions tables
-- review_schedule implements a 5-box Leitner system per (puzzle, user).
-- practice_sessions records completed training sessions.

CREATE TABLE review_schedule (
    puzzle_id    UUID        NOT NULL REFERENCES puzzles(id) ON DELETE CASCADE,
    user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    box          INTEGER     NOT NULL DEFAULT 1,
    due_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_result  BOOLEAN,
    streak       INTEGER     NOT NULL DEFAULT 0,
    PRIMARY KEY (puzzle_id, user_id)
);

CREATE INDEX idx_review_schedule_due ON review_schedule (user_id, due_at);

CREATE TABLE practice_sessions (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at    TIMESTAMPTZ,
    puzzles_total  INTEGER     NOT NULL DEFAULT 0,
    puzzles_solved INTEGER     NOT NULL DEFAULT 0,
    focus_types    JSONB       NOT NULL DEFAULT '[]',
    duration_ms    BIGINT
);

CREATE INDEX idx_sessions_user ON practice_sessions (user_id, started_at DESC);
