-- V8: convert puzzle TEXT[] columns to JSONB for Hibernate compatibility
-- JPA maps List<String> with @JdbcTypeCode(SqlTypes.JSON) to JSONB.
-- Must drop defaults before casting, then restore them.

-- solution_uci
ALTER TABLE puzzles ALTER COLUMN solution_uci DROP DEFAULT;
ALTER TABLE puzzles ALTER COLUMN solution_uci TYPE JSONB USING to_json(solution_uci);
ALTER TABLE puzzles ALTER COLUMN solution_uci SET DEFAULT '[]'::jsonb;

-- themes
ALTER TABLE puzzles ALTER COLUMN themes DROP DEFAULT;
ALTER TABLE puzzles ALTER COLUMN themes TYPE JSONB USING to_json(themes);
ALTER TABLE puzzles ALTER COLUMN themes SET DEFAULT '[]'::jsonb;
