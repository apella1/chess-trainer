-- V5: change NUMERIC(5,2) columns to DOUBLE PRECISION
-- Win probability values are floats from the formula; NUMERIC precision is unnecessary
-- and causes Hibernate schema validation type mismatches with Double fields.

ALTER TABLE move_evals
    ALTER COLUMN win_pct_before TYPE DOUBLE PRECISION,
    ALTER COLUMN win_pct_after TYPE DOUBLE PRECISION,
    ALTER COLUMN win_pct_loss TYPE DOUBLE PRECISION;

ALTER TABLE mistakes
    ALTER COLUMN severity TYPE DOUBLE PRECISION;
