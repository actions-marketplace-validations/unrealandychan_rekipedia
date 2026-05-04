"""Tests for MCP server ask tool (issue #59)."""
from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import patch, MagicMock


def _call_tool(name, args, symbols=None, rels=None):
    from rekipedia.cli.mcp_server import _handle_tool
    return _handle_tool(name, args, symbols or [], rels or [])


def test_ask_tool_returns_answer(tmp_path):
    repo = tmp_path
    rekipedia_dir = repo / ".rekipedia"
    rekipedia_dir.mkdir()

    with patch("rekipedia.orchestrator.run_ask.run_ask", return_value="The answer") as mock_ask:
        with patch("rekipedia.models.contracts.LLMConfig", return_value=MagicMock()):
            result_str = _call_tool("ask", {"question": "What does this do?", "repo": str(repo)})
    data = json.loads(result_str)
    assert data.get("answer") == "The answer"


def test_ask_tool_missing_rekipedia(tmp_path):
    result_str = _call_tool("ask", {"question": "What?", "repo": str(tmp_path)})
    data = json.loads(result_str)
    assert "error" in data
    assert "reki scan" in data["error"]


def test_search_nodes_still_works():
    symbols = [MagicMock(name="my_func", file="foo.py", kind="function")]
    symbols[0].name = "my_func"
    symbols[0].file = "foo.py"
    symbols[0].kind = "function"
    result_str = _call_tool("search_nodes", {"query": "my_func"}, symbols=symbols, rels=[])
    data = json.loads(result_str)
    assert len(data["matches"]) == 1
    assert data["matches"][0]["name"] == "my_func"


def test_get_context_still_works():
    symbols = [MagicMock()]
    symbols[0].name = "SomeClass"
    symbols[0].file = "bar.py"
    symbols[0].kind = "class"
    result_str = _call_tool("get_context", {"file": "bar.py"}, symbols=symbols, rels=[])
    data = json.loads(result_str)
    assert "symbols" in data
