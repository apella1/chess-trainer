-- V1: initial schema
-- Creates: users, service_heartbeats
-- This is the only migration that runs in Phase 0.
-- All other tables are added in subsequent migrations as features are built.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE users (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    chesscom_username TEXT        NOT NULL UNIQUE,
    display_name     TEXT        NOT NULL,
    rating_band      INTEGER,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Composite primary key: one row per (service, instance).
-- Workers upsert this row every few seconds.
-- The Status page reads it to determine if each service is alive.
CREATE TABLE service_heartbeats (
    service    TEXT        NOT NULL,
    instance   TEXT        NOT NULL,
    last_seen  TIMESTAMPTZ NOT NULL DEFAULT now(),
    details    JSONB       NOT NULL DEFAULT '{}',
    PRIMARY KEY (service, instance)
);
