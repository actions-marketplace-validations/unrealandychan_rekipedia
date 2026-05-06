"""Tests for tech lead notes in SqliteStore."""
from __future__ import annotations

from pathlib import Path

import pytest

from rekipedia.storage.sqlite_store import SqliteStore


@pytest.fixture
def store(tmp_path: Path) -> SqliteStore:
    s = SqliteStore(tmp_path / "store.db")
    s.open()
    yield s
    s.close()


def test_notes_table_created(store):
    assert "tech_lead_notes" in store.table_names()


def test_add_and_list_note(store):
    nid = store.upsert_note(content="Use Redis for caching", tags="arch,redis")
    notes = store.list_notes()
    assert len(notes) == 1
    assert notes[0]["content"] == "Use Redis for caching"
    assert notes[0]["tags"] == "arch,redis"
    assert notes[0]["id"] == nid


def test_list_empty(store):
    assert store.list_notes() == []


def test_delete_note(store):
    nid = store.upsert_note(content="Delete me", tags="")
    assert store.delete_note(nid) is True
    assert store.list_notes() == []


def test_delete_nonexistent(store):
    assert store.delete_note("nonexistent") is False


def test_tag_filter(store):
    store.upsert_note(content="ops note", tags="ops")
    store.upsert_note(content="auth note", tags="auth")
    store.upsert_note(content="both", tags="ops,auth")

    ops_notes = store.list_notes(tags="ops")
    assert all("ops" in n["tags"] for n in ops_notes)
    assert len(ops_notes) == 2

    auth_notes = store.list_notes(tags="auth")
    assert len(auth_notes) == 2


def test_upsert_updates_existing(store):
    nid = store.upsert_note(content="Original", tags="", note_id="test-uuid")
    store.upsert_note(content="Updated", tags="new", note_id="test-uuid")
    notes = store.list_notes()
    assert len(notes) == 1
    assert notes[0]["content"] == "Updated"
    assert notes[0]["tags"] == "new"


def test_get_note(store):
    nid = store.upsert_note(content="Test note", tags="test")
    note = store.get_note(nid)
    assert note is not None
    assert note["content"] == "Test note"
    assert store.get_note("nonexistent") is None


def test_get_notes_alias(store):
    store.upsert_note(content="Test", tags="")
    assert store.get_notes() == store.list_notes()
