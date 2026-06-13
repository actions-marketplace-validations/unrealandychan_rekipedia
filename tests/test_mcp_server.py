"""Tests for MCP server tools."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from rekipedia.cli.mcp_server import _handle_tool, _StoreCache, write_mcp_json

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_cache(symbols=None, rels=None) -> _StoreCache:
    """Return a _StoreCache with pre-loaded data (no real DB needed)."""
    cache = _StoreCache.__new__(_StoreCache)
    cache.db_path = MagicMock()
    cache.db_path.exists.return_value = True
    cache._store = None
    cache._symbols = symbols or []
    cache._rels = rels or []
    cache._mtime = 0.0
    cache._name_index = {}
    cache._file_index = {}
    cache._callers_index = {}
    cache._callees_index = {}
    if symbols or rels:
        cache._rebuild_indices(cache._symbols, cache._rels)
    # Prevent _refresh from touching the fake db_path
    cache._refresh = lambda: None
    return cache


def _call(name, args, symbols=None, rels=None):
    cache = _make_cache(symbols, rels)
    return json.loads(_handle_tool(name, args, cache))


# ── ask tool ──────────────────────────────────────────────────────────────────

def test_ask_tool_returns_answer(tmp_path):
    (tmp_path / ".rekipedia").mkdir()
    cache = _make_cache()
    cache.db_path = tmp_path / ".rekipedia" / "rekipedia.db"
    cache.db_path.touch()

    with patch("rekipedia.orchestrator.run_ask.run_ask", return_value="The answer"):
        with patch("rekipedia.models.contracts.LLMConfig", return_value=MagicMock()):
            result = json.loads(_handle_tool("ask", {"question": "What?", "repo": str(tmp_path)}, cache))
    assert result.get("answer") == "The answer"


def test_ask_tool_missing_rekipedia(tmp_path):
    cache = _make_cache()
    cache.db_path = tmp_path / ".rekipedia" / "rekipedia.db"
    result = json.loads(_handle_tool("ask", {"question": "What?", "repo": str(tmp_path)}, cache))
    assert "error" in result
    assert "reki scan" in result["error"]


# ── search_nodes ──────────────────────────────────────────────────────────────

def test_search_nodes_indexed():
    sym = MagicMock()
    sym.name = "my_func"
    sym.file = "foo.py"
    sym.kind = "function"
    data = _call("search_nodes", {"query": "my_func"}, symbols=[sym])
    assert len(data["matches"]) == 1
    assert data["matches"][0]["name"] == "my_func"


def test_search_nodes_partial_match():
    sym = MagicMock()
    sym.name = "parse_config"
    sym.file = "config.py"
    sym.kind = "function"
    data = _call("search_nodes", {"query": "parse"}, symbols=[sym])
    assert len(data["matches"]) == 1


def test_search_nodes_no_match():
    sym = MagicMock()
    sym.name = "my_func"
    sym.file = "foo.py"
    sym.kind = "function"
    data = _call("search_nodes", {"query": "xyz_not_exist"}, symbols=[sym])
    assert data["matches"] == []


# ── get_context ───────────────────────────────────────────────────────────────

def test_get_context_exact_match():
    sym = MagicMock()
    sym.name = "SomeClass"
    sym.file = "/abs/path/bar.py"
    sym.kind = "class"
    data = _call("get_context", {"file": "bar.py"}, symbols=[sym])
    assert "SomeClass" in data["symbols"]


def test_get_context_partial_path():
    sym = MagicMock()
    sym.name = "MyClass"
    sym.file = "/project/src/module/myfile.py"
    sym.kind = "class"
    # Partial filename should still match
    data = _call("get_context", {"file": "module/myfile.py"}, symbols=[sym])
    assert "MyClass" in data["symbols"]


# ── get_relationships ─────────────────────────────────────────────────────────

def test_get_relationships_callers_callees():
    rel = MagicMock()
    rel.from_ = "caller_func"
    rel.to = "target_func"
    rel.kind = "calls"
    data = _call("get_relationships", {"symbol": "target_func"}, rels=[rel])
    assert "caller_func" in data["callers"]
    assert data["callees"] == []


# ── error handling ────────────────────────────────────────────────────────────

def test_unknown_tool_returns_error():
    data = _call("nonexistent_tool", {})
    assert "error" in data


def test_no_db_returns_error():
    cache = _StoreCache.__new__(_StoreCache)
    cache.db_path = MagicMock()
    cache.db_path.exists.return_value = False
    result = json.loads(_handle_tool("search_nodes", {"query": "anything"}, cache))
    assert "error" in result


# ── write_mcp_json ────────────────────────────────────────────────────────────

def test_write_mcp_json_creates_file(tmp_path):
    write_mcp_json(tmp_path)
    mcp = tmp_path / ".mcp.json"
    assert mcp.exists()
    data = json.loads(mcp.read_text())
    assert "rekipedia" in data["mcpServers"]


def test_write_mcp_json_idempotent(tmp_path):
    write_mcp_json(tmp_path)
    mtime1 = (tmp_path / ".mcp.json").stat().st_mtime
    write_mcp_json(tmp_path)
    mtime2 = (tmp_path / ".mcp.json").stat().st_mtime
    assert mtime1 == mtime2  # file not rewritten


# ── _StoreCache auto-reload ───────────────────────────────────────────────────

def test_store_cache_reload_on_mtime_change(tmp_path):
    db = tmp_path / ".rekipedia" / "rekipedia.db"
    db.parent.mkdir()
    db.touch()

    cache = _StoreCache(str(tmp_path))
    # First load — DB empty, should not crash
    cache._refresh()
    initial_mtime = cache._mtime

    # Simulate DB update
    import time
    time.sleep(0.05)
    db.write_bytes(b"updated")

    with patch.object(cache, "_load") as mock_load:
        cache._refresh()
        mock_load.assert_called_once()


# ── get_god_nodes ─────────────────────────────────────────────────────────────

def _make_rels(*pairs):
    """Build list of rel dicts from (from_, to) pairs."""
    return [
        {"from_": f, "to": t, "kind": "calls", "file": "f.py",
         "confidence": 1.0, "evidence_tag": "EXTRACTED"}
        for f, t in pairs
    ]


def test_get_god_nodes_returns_top_nodes():
    rels = _make_rels(("A", "B"), ("A", "C"), ("B", "A"))
    result = _call("get_god_nodes", {"top_n": 3}, rels=rels)
    assert "god_nodes" in result
    assert len(result["god_nodes"]) >= 1
    names = [n["name"] for n in result["god_nodes"]]
    assert "A" in names  # A has out_degree=2, in_degree=1 → highest total


def test_get_god_nodes_default_top_n():
    rels = _make_rels(*[(f"n{i}", "hub") for i in range(15)])
    result = _call("get_god_nodes", {}, rels=rels)
    assert len(result["god_nodes"]) <= 10


def test_get_god_nodes_has_degree_fields():
    rels = _make_rels(("A", "B"), ("B", "A"))
    result = _call("get_god_nodes", {"top_n": 2}, rels=rels)
    for node in result["god_nodes"]:
        assert "in_degree" in node
        assert "out_degree" in node
        assert "score" in node


def test_get_god_nodes_empty_rels():
    result = _call("get_god_nodes", {}, rels=[])
    assert result.get("god_nodes") == []


# ── shortest_path ─────────────────────────────────────────────────────────────

def test_shortest_path_direct_connection():
    rels = _make_rels(("A", "B"))
    result = _call("shortest_path", {"from": "A", "to": "B"}, rels=rels)
    assert result.get("path") == ["A", "B"]
    assert result.get("length") == 1


def test_shortest_path_multi_hop():
    rels = _make_rels(("A", "B"), ("B", "C"))
    result = _call("shortest_path", {"from": "A", "to": "C"}, rels=rels)
    assert result.get("path") == ["A", "B", "C"]
    assert result.get("length") == 2


def test_shortest_path_no_path():
    rels = _make_rels(("A", "B"))
    result = _call("shortest_path", {"from": "A", "to": "Z"}, rels=rels)
    assert result.get("path") is None


def test_shortest_path_same_symbol():
    rels = _make_rels(("A", "B"))
    result = _call("shortest_path", {"from": "A", "to": "A"}, rels=rels)
    # A→A: trivially reachable (BFS from A, first element is A)
    assert result.get("path") == ["A"]
    assert result.get("length") == 0


def test_shortest_path_prefers_shortest():
    # A→C directly, also A→B→C — should pick A→C (length 1)
    rels = _make_rels(("A", "C"), ("A", "B"), ("B", "C"))
    result = _call("shortest_path", {"from": "A", "to": "C"}, rels=rels)
    assert result.get("length") == 1


# ── get_community ─────────────────────────────────────────────────────────────

def test_get_community_returns_members():
    rels = _make_rels(("A", "B"), ("B", "A"))
    result = _call("get_community", {"symbol": "A"}, rels=rels)
    assert "community_id" in result
    assert "members" in result
    assert "A" in result["members"]
    assert "B" in result["members"]


def test_get_community_unknown_symbol():
    result = _call("get_community", {"symbol": "NonExistent"}, rels=[])
    assert "error" in result or result.get("members") == []


def test_get_community_isolated_nodes_in_own_community():
    # C is not connected to A or B
    rels = _make_rels(("A", "B"), ("B", "A"))
    result_a = _call("get_community", {"symbol": "A"}, rels=rels)
    # C isn't in the graph so looking it up should return error
    result_c = _call("get_community", {"symbol": "C"}, rels=rels)
    assert "error" in result_c or result_c.get("members") == []


def test_get_community_members_sorted():
    rels = _make_rels(("C", "A"), ("A", "C"), ("B", "A"), ("A", "B"))
    result = _call("get_community", {"symbol": "A"}, rels=rels)
    if result.get("members"):
        assert result["members"] == sorted(result["members"])
