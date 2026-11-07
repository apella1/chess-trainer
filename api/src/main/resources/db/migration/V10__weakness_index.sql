-- V10: add index to support weakness aggregation queries
-- The idx_mistakes_user_type index already exists from V4,
-- but we add a covering index for the phase column too.
CREATE INDEX IF NOT EXISTS idx_mistakes_user_type_phase 
    ON mistakes (user_id, type, phase);
