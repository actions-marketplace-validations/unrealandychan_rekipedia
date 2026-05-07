-- Migration 005: page_sources — tracks which source files contributed to each wiki page
-- Enables targeted wiki re-synthesis in reki update (issue #77)
CREATE TABLE IF NOT EXISTS page_sources (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT    NOT NULL,
    page_slug   TEXT    NOT NULL,
    file_path   TEXT    NOT NULL,
    UNIQUE (run_id, page_slug, file_path)
);
CREATE INDEX IF NOT EXISTS idx_page_sources_run ON page_sources(run_id);
CREATE INDEX IF NOT EXISTS idx_page_sources_slug ON page_sources(run_id, page_slug);
INSERT INTO schema_version (version, applied_at) VALUES (5, datetime('now'));
