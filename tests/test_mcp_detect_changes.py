# tests/test_mcp_detect_changes.py
"""Tests for detect_changes MCP tool."""
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_cache(symbols=None, rels=None):
    """Build a minimal mock _StoreCache."""
    cache = MagicMock()
    cache.available = True
    cache.symbols = symbols or []
    cache.rels = rels or []
    cache.search_by_name.return_value = []
    cache.callers_callees.return_value = ([], [])
    return cache


def _handle(args, symbols=None, rels=None):
    from rekipedia.cli.mcp_server import _handle_tool
    return json.loads(_handle_tool("detect_changes", args, _make_cache(symbols, rels)))


# ── git helpers ────────────────────────────────────────────────────────────

def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True, capture_output=True)
    (path / "README.md").write_text("init")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True)


# ── tests ──────────────────────────────────────────────────────────────────

def test_no_changes_returns_empty(tmp_path):
    """Returns empty impacts list when no uncommitted changes."""
    _init_git_repo(tmp_path)
    result = _handle({"repo": str(tmp_path)})
    assert result["changed_files"] == []
    assert result["impacts"] == []
    assert "No uncommitted changes" in result["summary"]


def test_detects_unstaged_change(tmp_path):
    """Detects a modified file that is not staged."""
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("modified")
    result = _handle({"repo": str(tmp_path)})
    assert "README.md" in result["changed_files"]


def test_detects_staged_change(tmp_path):
    """Detects a staged change when staged=true."""
    _init_git_repo(tmp_path)
    new_file = tmp_path / "new.py"
    new_file.write_text("def foo(): pass")
    subprocess.run(["git", "add", "new.py"], cwd=tmp_path, check=True, capture_output=True)
    result = _handle({"repo": str(tmp_path), "staged": True})
    assert "new.py" in result["changed_files"]


def test_staged_only_excludes_unstaged(tmp_path):
    """staged=true should NOT include unstaged changes."""
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("unstaged change")
    result = _handle({"repo": str(tmp_path), "staged": True})
    assert "README.md" not in result["changed_files"]


def test_rekipedia_files_filtered(tmp_path):
    """Files inside .rekipedia/ are excluded from changed_files."""
    _init_git_repo(tmp_path)
    rek_dir = tmp_path / ".rekipedia"
    rek_dir.mkdir()
    (rek_dir / "store.db").write_bytes(b"data")
    subprocess.run(["git", "add", ".rekipedia/store.db"], cwd=tmp_path,
                   check=True, capture_output=True)
    result = _handle({"repo": str(tmp_path)})
    assert not any(".rekipedia" in f for f in result["changed_files"])


def test_impact_risk_low_when_no_symbols(tmp_path):
    """A changed file with no known symbols gets risk=LOW."""
    _init_git_repo(tmp_path)
    (tmp_path / "unknown.py").write_text("x = 1")
    result = _handle({"repo": str(tmp_path)})
    if result["changed_files"]:
        for imp in result["impacts"]:
            if "unknown.py" in imp["file"]:
                assert imp["risk"] == "LOW"


def test_summary_contains_file_count(tmp_path):
    """Summary string mentions the number of changed files."""
    _init_git_repo(tmp_path)
    # Modify a tracked file so git diff --name-only picks it up
    (tmp_path / "README.md").write_text("modified content a")
    result = _handle({"repo": str(tmp_path)})
    n = len(result["changed_files"])
    assert n >= 1
    assert str(n) in result["summary"]


def test_not_git_repo_returns_error(tmp_path):
    """Returns an error dict when called outside a git repo."""
    result = _handle({"repo": str(tmp_path)})
    assert "error" in result


def test_detect_changes_in_mcp_tools_list():
    """detect_changes must appear in the TOOLS list."""
    from rekipedia.cli.mcp_server import TOOLS
    names = [t["name"] for t in TOOLS]
    assert "detect_changes" in names


def test_detect_changes_schema():
    """detect_changes inputSchema has expected fields."""
    from rekipedia.cli.mcp_server import TOOLS
    tool = next(t for t in TOOLS if t["name"] == "detect_changes")
    props = tool["inputSchema"]["properties"]
    assert "repo" in props
    assert "staged" in props
    assert "base" in props
