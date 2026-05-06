-- Migration 003: tech_lead_notes table
CREATE TABLE IF NOT EXISTS tech_lead_notes (
    id         TEXT PRIMARY KEY,
    content    TEXT NOT NULL,
    tags       TEXT NOT NULL DEFAULT '',
    source     TEXT NOT NULL DEFAULT 'manual',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
INSERT INTO schema_version (version, applied_at) VALUES (3, datetime('now'));
