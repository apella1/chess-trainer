-- V4: analysis tables
-- Creates: analysis_jobs (job queue), moves, analysis_runs, move_evals, mistakes
-- The worker claims analysis_jobs via SELECT ... FOR UPDATE SKIP LOCKED,
-- runs Stockfish on each position, and writes results to the other tables.

-- Job queue: workers claim rows from this table
CREATE TABLE analysis_jobs (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    game_id      UUID        REFERENCES games(id) ON DELETE CASCADE,
    kind         TEXT        NOT NULL,
    status       TEXT        NOT NULL DEFAULT 'pending',
    attempts     INTEGER     NOT NULL DEFAULT 0,
    max_attempts INTEGER     NOT NULL DEFAULT 3,
    locked_by    TEXT,
    locked_at    TIMESTAMPTZ,
    last_error   TEXT,
    payload      JSONB       NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at   TIMESTAMPTZ,
    finished_at  TIMESTAMPTZ
);

CREATE INDEX idx_jobs_pending ON analysis_jobs (created_at) WHERE status = 'pending';

-- One row per half-move (ply) in a game
CREATE TABLE moves (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id             UUID        NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    ply                 INTEGER     NOT NULL,
    color               TEXT        NOT NULL,
    san                 TEXT        NOT NULL,
    uci                 TEXT,
    fen_before          TEXT        NOT NULL,
    fen_after           TEXT        NOT NULL,
    clock_ms_remaining  BIGINT,
    time_spent_ms       BIGINT,
    UNIQUE (game_id, ply)
);

CREATE INDEX idx_moves_game ON moves (game_id, ply);

-- Records the exact engine settings used for an analysis run
CREATE TABLE analysis_runs (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id        UUID        NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    engine_name    TEXT        NOT NULL,
    engine_version TEXT,
    depth          INTEGER     NOT NULL,
    multipv        INTEGER     NOT NULL,
    status         TEXT        NOT NULL DEFAULT 'running',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Engine evaluation per move (all from the mover's perspective)
CREATE TABLE move_evals (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id               UUID        NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    move_id              UUID        NOT NULL REFERENCES moves(id) ON DELETE CASCADE,
    eval_before_cp       INTEGER,
    eval_after_cp        INTEGER,
    mate_before          INTEGER,
    mate_after           INTEGER,
    best_uci             TEXT,
    best_eval_cp         INTEGER,
    second_best_eval_cp  INTEGER,
    pv_json              JSONB,
    win_pct_before       NUMERIC(5,2),
    win_pct_after        NUMERIC(5,2),
    win_pct_loss         NUMERIC(5,2),
    classification      TEXT
);

CREATE INDEX idx_move_evals_move ON move_evals (move_id);

-- Classified mistakes from the user's moves
CREATE TABLE mistakes (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id          UUID        NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    user_id          UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    move_eval_id     UUID        NOT NULL REFERENCES move_evals(id) ON DELETE CASCADE,
    kind             TEXT        NOT NULL,
    type             TEXT,
    tags             TEXT[],
    phase            TEXT,
    severity          NUMERIC(5,2),
    material_swing_cp INTEGER
);

CREATE INDEX idx_mistakes_user_type ON mistakes (user_id, type);
CREATE INDEX idx_mistakes_game ON mistakes (game_id);
