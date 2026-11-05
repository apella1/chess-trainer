-- V3: synced_archives table
-- Tracks which chess.com monthly archives have already been fully processed.
-- On re-sync, the sync service skips archives already in this table and only
-- fetches new ones, plus re-checks the most recent synced archive (the current
-- month may have new games added since the last sync).

CREATE TABLE synced_archives (
    user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    archive_url  TEXT        NOT NULL,
    synced_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, archive_url)
);
