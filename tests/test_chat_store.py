# tests/test_chat_store.py
"""Tests for ChatStore — isolated chat history in chat.db."""
from pathlib import Path


def test_chat_db_created_separately(tmp_path):
    """chat.db is created at output_dir/chat.db, not as store.db."""
    from rekipedia.storage.chat_store import ChatStore, _chat_db_path

    with ChatStore(tmp_path) as cs:
        cs.save_qa("/repo", "hello?", "world.", "gpt-4")

    assert (tmp_path / "chat.db").exists()
    assert not (tmp_path / "store.db").exists()
    assert _chat_db_path(tmp_path) == tmp_path / "chat.db"


def test_save_and_retrieve_qa(tmp_path):
    """Saved Q&A is retrievable and correctly round-trips."""
    from rekipedia.storage.chat_store import ChatStore

    with ChatStore(tmp_path) as cs:
        qa_id = cs.save_qa("/repo/myproject", "What does foo do?", "It does bar.", "claude-3")
        history = cs.get_qa_history("/repo/myproject")

    assert len(history) == 1
    entry = history[0]
    assert entry["id"] == qa_id
    assert entry["question"] == "What does foo do?"
    assert entry["answer"] == "It does bar."
    assert entry["model"] == "claude-3"
    assert "created_at" in entry


def test_history_newest_first(tmp_path):
    """History is returned newest first."""
    from rekipedia.storage.chat_store import ChatStore

    with ChatStore(tmp_path) as cs:
        cs.save_qa("/r", "q1", "a1", "")
        cs.save_qa("/r", "q2", "a2", "")
        cs.save_qa("/r", "q3", "a3", "")
        history = cs.get_qa_history("/r")

    assert [h["question"] for h in history] == ["q3", "q2", "q1"]


def test_history_scoped_by_repo(tmp_path):
    """History from different repos does not bleed."""
    from rekipedia.storage.chat_store import ChatStore

    with ChatStore(tmp_path) as cs:
        cs.save_qa("/repo/a", "qa", "aa", "")
        cs.save_qa("/repo/b", "qb", "ab", "")
        hist_a = cs.get_qa_history("/repo/a")
        hist_b = cs.get_qa_history("/repo/b")

    assert len(hist_a) == 1
    assert hist_a[0]["question"] == "qa"
    assert len(hist_b) == 1
    assert hist_b[0]["question"] == "qb"


def test_symbol_mentions_saved(tmp_path):
    """Symbol mentions are persisted to qa_symbol_mentions."""
    from rekipedia.storage.chat_store import ChatStore

    with ChatStore(tmp_path) as cs:
        qa_id = cs.save_qa("/r", "q", "a", "")
        cs.save_qa_symbol_mentions(qa_id, ["MyClass", "my_func"])
        # Read back via raw connection to verify
        rows = cs._conn.execute(
            "SELECT symbol_name FROM qa_symbol_mentions WHERE qa_id=?", (qa_id,)
        ).fetchall()
        assert {r[0] for r in rows} == {"MyClass", "my_func"}


def test_clear_history(tmp_path):
    """clear_history removes all entries for a repo."""
    from rekipedia.storage.chat_store import ChatStore

    with ChatStore(tmp_path) as cs:
        id1 = cs.save_qa("/r", "q1", "a1", "")
        cs.save_qa_symbol_mentions(id1, ["SomeSymbol"])
        cs.save_qa("/r", "q2", "a2", "")
        deleted = cs.clear_history("/r")
        assert deleted == 2
        assert cs.get_qa_history("/r") == []
        # Symbol mentions should be gone too
        rows = cs._conn.execute("SELECT * FROM qa_symbol_mentions").fetchall()
        assert rows == []


def test_delete_qa(tmp_path):
    """delete_qa removes a single entry."""
    from rekipedia.storage.chat_store import ChatStore

    with ChatStore(tmp_path) as cs:
        id1 = cs.save_qa("/r", "q1", "a1", "")
        _id2 = cs.save_qa("/r", "q2", "a2", "")
        cs.delete_qa(id1)
        history = cs.get_qa_history("/r")
        assert len(history) == 1
        assert history[0]["question"] == "q2"


def test_history_limit(tmp_path):
    """limit parameter caps the number of results."""
    from rekipedia.storage.chat_store import ChatStore

    with ChatStore(tmp_path) as cs:
        for i in range(10):
            cs.save_qa("/r", f"q{i}", f"a{i}", "")
        history = cs.get_qa_history("/r", limit=3)
    assert len(history) == 3


def test_context_manager_closes(tmp_path):
    """ChatStore closes connection on context exit."""
    from rekipedia.storage.chat_store import ChatStore

    cs = ChatStore(tmp_path)
    with cs:
        assert cs._conn is not None
    assert cs._conn is None
