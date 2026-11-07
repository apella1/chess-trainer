-- V7: convert puzzle difficulty_est to DOUBLE PRECISION only
-- (solution_uci and themes are fixed in V8)
ALTER TABLE puzzles
    ALTER COLUMN difficulty_est TYPE DOUBLE PRECISION;
