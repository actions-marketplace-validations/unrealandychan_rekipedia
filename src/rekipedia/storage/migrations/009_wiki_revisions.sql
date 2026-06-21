-- Migration 009: Wiki revisions support for self-consolidating wiki updates

CREATE TABLE IF NOT EXISTS wiki_revisions (
    slug TEXT PRIMARY KEY,
    run_id TEXT,
    title TEXT,
    content TEXT,
    updated_at TEXT
);
