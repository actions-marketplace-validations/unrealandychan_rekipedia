-- Migration 006: document_chunks table for PDF/DOCX/PPTX/XLSX content
CREATE TABLE IF NOT EXISTS document_chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT NOT NULL,
    doc_path    TEXT NOT NULL,
    page_number INTEGER NOT NULL DEFAULT 1,
    text        TEXT NOT NULL,
    bbox_json   TEXT
);
CREATE INDEX IF NOT EXISTS idx_document_chunks_run ON document_chunks(run_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_path ON document_chunks(run_id, doc_path);
