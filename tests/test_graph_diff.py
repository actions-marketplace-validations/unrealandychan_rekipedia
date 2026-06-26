# tests/test_graph_diff.py
"""Tests for compute_graph_diff and reki diff --graph-diff."""
import json

import pytest

from rekipedia.cli.diff import compute_graph_diff, _edge_key


# ── unit tests for compute_graph_diff ────────────────────────────────────────

def _rel(frm: str, to: str, kind: str = "calls") -> dict:
    return {"from_": frm, "to": to, "kind": kind}


def test_empty_both():
    """No edges in either snapshot → no diff."""
    diff = compute_graph_diff([], [])
    assert diff["added"] == []
    assert diff["removed"] == []
    assert diff["unchanged_count"] == 0
    assert "+0 edges added, -0 edges removed" in diff["summary"]


def test_all_added():
    """All edges in new_rels are additions."""
    new = [_rel("A", "B"), _rel("B", "C")]
    diff = compute_graph_diff([], new)
    assert len(diff["added"]) == 2
    assert diff["removed"] == []
    assert diff["unchanged_count"] == 0


def test_all_removed():
    """All edges in old_rels are removals."""
    old = [_rel("A", "B"), _rel("B", "C")]
    diff = compute_graph_diff(old, [])
    assert diff["added"] == []
    assert len(diff["removed"]) == 2
    assert diff["unchanged_count"] == 0


def test_identical_snapshots():
    """Identical snapshots → no changes."""
    rels = [_rel("A", "B"), _rel("B", "C"), _rel("C", "D")]
    diff = compute_graph_diff(rels, rels)
    assert diff["added"] == []
    assert diff["removed"] == []
    assert diff["unchanged_count"] == 3


def test_partial_change():
    """One added, one removed, one unchanged."""
    old = [_rel("A", "B"), _rel("B", "C")]
    new = [_rel("A", "B"), _rel("C", "D")]
    diff = compute_graph_diff(old, new)
    assert len(diff["added"]) == 1
    assert len(diff["removed"]) == 1
    assert diff["unchanged_count"] == 1
    added_key = _edge_key(diff["added"][0])
    assert added_key == ("C", "D", "calls")
    removed_key = _edge_key(diff["removed"][0])
    assert removed_key == ("B", "C", "calls")


def test_kind_matters():
    """Same from/to but different kind → treated as different edge."""
    old = [_rel("A", "B", "calls")]
    new = [_rel("A", "B", "imports")]
    diff = compute_graph_diff(old, new)
    assert len(diff["added"]) == 1
    assert len(diff["removed"]) == 1
    assert diff["unchanged_count"] == 0


def test_edge_key_from_underscore():
    """_edge_key handles both 'from_' and 'from' field names."""
    r1 = {"from_": "X", "to": "Y", "kind": "calls"}
    r2 = {"from": "X", "to": "Y", "kind": "calls"}
    assert _edge_key(r1) == _edge_key(r2)


def test_summary_string_format():
    """Summary describes add/remove/unchanged counts."""
    old = [_rel("A", "B"), _rel("B", "C"), _rel("C", "D")]
    new = [_rel("A", "B"), _rel("X", "Y")]
    diff = compute_graph_diff(old, new)
    assert "+1 edges added" in diff["summary"]
    assert "-2 edges removed" in diff["summary"]
    assert "1 unchanged" in diff["summary"]


def test_duplicate_edges_deduped():
    """Duplicate edges in a snapshot should not double-count."""
    edge = _rel("A", "B")
    diff = compute_graph_diff([edge, edge], [edge])
    # Dedup by key → treated as 1 unchanged
    assert diff["unchanged_count"] == 1
    assert diff["added"] == []
    assert diff["removed"] == []


# ── integration: get_two_latest_run_ids ───────────────────────────────────────

def test_get_two_latest_run_ids_no_runs(tmp_path):
    """Returns (None, None) when no runs exist."""
    from rekipedia.storage.sqlite_store import SqliteStore
    db = tmp_path / "store.db"
    with SqliteStore(db) as s:
        s.upsert_run("r1", str(tmp_path), "running")  # ensure table exists
        # delete it
        s._c.execute("DELETE FROM scan_runs")
        s._c.commit()
        latest, prev = s.get_two_latest_run_ids(str(tmp_path))
    assert latest is None
    assert prev is None


def test_get_two_latest_run_ids_one_run(tmp_path):
    """Returns (latest, None) when only one run exists."""
    from rekipedia.storage.sqlite_store import SqliteStore
    db = tmp_path / "store.db"
    with SqliteStore(db) as s:
        s.upsert_run("run-a", str(tmp_path), "success")
        s.update_run_status("run-a", "success")
        latest, prev = s.get_two_latest_run_ids(str(tmp_path))
    assert latest == "run-a"
    assert prev is None


def test_get_two_latest_run_ids_two_runs(tmp_path):
    """Returns (latest, previous) when two runs exist."""
    import time
    from rekipedia.storage.sqlite_store import SqliteStore
    db = tmp_path / "store.db"
    with SqliteStore(db) as s:
        s.upsert_run("run-old", str(tmp_path), "success")
        s.update_run_status("run-old", "success")
        time.sleep(0.01)
        s.upsert_run("run-new", str(tmp_path), "success")
        s.update_run_status("run-new", "success")
        latest, prev = s.get_two_latest_run_ids(str(tmp_path))
    assert latest == "run-new"
    assert prev == "run-old"
