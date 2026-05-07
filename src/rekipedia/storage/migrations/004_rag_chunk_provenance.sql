-- Migration 004: RAG chunk provenance table
-- Stores per-chunk provenance for incremental re-embedding (issue #75)
CREATE TABLE IF NOT EXISTS rag_chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT    NOT NULL,
    file_path   TEXT    NOT NULL,
    chunk_idx   INTEGER NOT NULL,
    start_line  INTEGER NOT NULL,
    end_line    INTEGER NOT NULL,
    start_char  INTEGER NOT NULL,
    end_char    INTEGER NOT NULL,
    text_hash   TEXT    NOT NULL,   -- SHA-256 of chunk text
    is_code     INTEGER NOT NULL DEFAULT 1,
    is_implementation INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (run_id, file_path, chunk_idx)
);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_file ON rag_chunks(run_id, file_path);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_hash ON rag_chunks(text_hash);
INSERT INTO schema_version (version, applied_at) VALUES (4, datetime('now'));
