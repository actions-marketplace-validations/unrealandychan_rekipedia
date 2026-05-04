"""Tests for compute_impact."""
from rekipedia.analysis.impact import compute_impact


def make_sym(name, file):
    return {"name": name, "file": file}


def make_rel(frm, to, kind="calls"):
    return {"from_": frm, "to": to, "kind": kind}


def test_direct_callers_included():
    symbols = [
        make_sym("foo", "src/a.py"),
        make_sym("bar", "src/b.py"),
    ]
    rels = [make_rel("bar", "foo")]
    result = compute_impact("src/a.py", rels, symbols, depth=2)
    assert "bar" in result["affected_symbols"]
    assert "src/b.py" in result["affected_files"]


def test_bfs_stops_at_depth():
    symbols = [
        make_sym("foo", "src/a.py"),
        make_sym("bar", "src/b.py"),
        make_sym("baz", "src/c.py"),
        make_sym("qux", "src/d.py"),
    ]
    # foo <- bar <- baz <- qux
    rels = [
        make_rel("bar", "foo"),
        make_rel("baz", "bar"),
        make_rel("qux", "baz"),
    ]
    result = compute_impact("src/a.py", rels, symbols, depth=2)
    assert "bar" in result["affected_symbols"]
    assert "baz" in result["affected_symbols"]
    assert "qux" not in result["affected_symbols"]


def test_related_tests_identified():
    symbols = [
        make_sym("foo", "src/a.py"),
        make_sym("test_foo", "tests/test_a.py"),
    ]
    rels = [make_rel("test_foo", "foo")]
    result = compute_impact("src/a.py", rels, symbols, depth=1)
    assert "tests/test_a.py" in result["related_tests"]


def test_empty_graph_returns_empty():
    result = compute_impact("src/a.py", [], [], depth=2)
    assert result["affected_symbols"] == []
    assert result["affected_files"] == []
    assert result["related_tests"] == []
    assert result["total_affected"] == 0
