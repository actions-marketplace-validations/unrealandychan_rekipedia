"""Tests for document_chunks SQLite storage."""
from __future__ import annotations
import tempfile
from pathlib import Path

import pytest

from rekipedia.storage.sqlite_store import SqliteStore


@pytest.fixture()
def store(tmp_path):
    db = tmp_path / "store.db"
    s = SqliteStore(db)
    s.open()
    yield s
    s.close()


def test_upsert_and_get_document_chunks(store):
    run_id = "test-run-001"
    store.upsert_run(run_id, "/tmp/repo")

    chunks = [
        {"doc_path": "docs/api.pdf", "page_number": 1, "text": "Introduction", "bounding_box": {}},
        {"doc_path": "docs/api.pdf", "page_number": 2, "text": "API Reference", "bounding_box": {"x": 10, "y": 20}},
    ]
    store.upsert_document_chunks(run_id, chunks)

    result = store.get_document_chunks(run_id)
    assert len(result) == 2
    assert result[0]["text"] == "Introduction"
    assert result[1]["page_number"] == 2


def test_get_document_chunks_filtered_by_path(store):
    run_id = "test-run-002"
    store.upsert_run(run_id, "/tmp/repo")

    chunks = [
        {"doc_path": "docs/api.pdf", "page_number": 1, "text": "API page 1", "bounding_box": {}},
        {"doc_path": "docs/guide.docx", "page_number": 1, "text": "Guide page 1", "bounding_box": {}},
    ]
    store.upsert_document_chunks(run_id, chunks)

    result = store.get_document_chunks(run_id, doc_path="docs/api.pdf")
    assert len(result) == 1
    assert result[0]["doc_path"] == "docs/api.pdf"


def test_document_chunks_empty_run(store):
    run_id = "test-run-003"
    store.upsert_run(run_id, "/tmp/repo")
    result = store.get_document_chunks(run_id)
    assert result == []


def test_document_chunks_bbox_roundtrip(store):
    run_id = "test-run-004"
    store.upsert_run(run_id, "/tmp/repo")

    bbox = {"x": 12.5, "y": 30.0, "w": 200.0, "h": 15.0}
    store.upsert_document_chunks(run_id, [
        {"doc_path": "report.pdf", "page_number": 1, "text": "Hello", "bounding_box": bbox}
    ])

    result = store.get_document_chunks(run_id)
    assert result[0]["bounding_box"] == bbox
