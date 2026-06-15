CREATE TABLE IF NOT EXISTS qa_symbol_mentions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    qa_id       INTEGER NOT NULL,
    symbol_name TEXT NOT NULL,
    UNIQUE (qa_id, symbol_name)
);
INSERT OR IGNORE INTO schema_version (version) VALUES (7);
