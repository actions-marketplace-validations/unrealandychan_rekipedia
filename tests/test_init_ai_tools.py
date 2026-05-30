"""Tests for --with-copilot, --with-codex, --with-cursor, --with-all-ai flags."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from rekipedia.cli.init import init_cmd


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    return tmp_path


def invoke(repo: Path, *args):
    runner = CliRunner()
    return runner.invoke(init_cmd, [str(repo)] + list(args))


def test_with_copilot_creates_vscode_mcp_json(repo: Path):
    result = invoke(repo, "--with-copilot")
    assert result.exit_code == 0
    mcp_path = repo / ".vscode" / "mcp.json"
    assert mcp_path.exists()
    data = json.loads(mcp_path.read_text())
    assert "servers" in data
    assert "rekipedia" in data["servers"]
    assert data["servers"]["rekipedia"]["type"] == "stdio"
    assert data["servers"]["rekipedia"]["command"] == "reki"
    assert data["servers"]["rekipedia"]["args"] == ["mcp"]


def test_with_copilot_creates_vscode_settings(repo: Path):
    result = invoke(repo, "--with-copilot")
    assert result.exit_code == 0
    settings_path = repo / ".vscode" / "settings.json"
    assert settings_path.exists()
    data = json.loads(settings_path.read_text())
    assert data["chat.mcp.enabled"] is True


def test_with_copilot_merges_existing_settings(repo: Path):
    vscode_dir = repo / ".vscode"
    vscode_dir.mkdir()
    (vscode_dir / "settings.json").write_text(json.dumps({"editor.fontSize": 14}))
    invoke(repo, "--with-copilot")
    data = json.loads((vscode_dir / "settings.json").read_text())
    assert data["chat.mcp.enabled"] is True
    assert data["editor.fontSize"] == 14


def test_with_codex_creates_hint_md(repo: Path):
    result = invoke(repo, "--with-codex")
    assert result.exit_code == 0
    hint_path = repo / "codex-mcp-hint.md"
    assert hint_path.exists()
    content = hint_path.read_text()
    assert "rekipedia MCP server" in content
    assert "[[mcp_servers]]" in content


def test_with_codex_creates_instructions_md(repo: Path):
    result = invoke(repo, "--with-codex")
    assert result.exit_code == 0
    instructions_path = repo / ".codex" / "instructions.md"
    assert instructions_path.exists()
    content = instructions_path.read_text()
    assert "rekipedia" in content
    assert "list_wiki_pages" in content


def test_with_cursor_creates_mcp_json(repo: Path):
    result = invoke(repo, "--with-cursor")
    assert result.exit_code == 0
    mcp_path = repo / ".cursor" / "mcp.json"
    assert mcp_path.exists()
    data = json.loads(mcp_path.read_text())
    assert "mcpServers" in data
    assert "rekipedia" in data["mcpServers"]
    assert data["mcpServers"]["rekipedia"]["command"] == "reki"


def test_with_cursor_creates_rules_mdc(repo: Path):
    result = invoke(repo, "--with-cursor")
    assert result.exit_code == 0
    rules_path = repo / ".cursor" / "rules" / "rekipedia.mdc"
    assert rules_path.exists()
    content = rules_path.read_text()
    assert "alwaysApply: true" in content
    assert "rekipedia" in content


def test_with_all_ai_creates_all_files(repo: Path):
    result = invoke(repo, "--with-all-ai")
    assert result.exit_code == 0
    assert (repo / ".vscode" / "mcp.json").exists()
    assert (repo / ".vscode" / "settings.json").exists()
    assert (repo / "codex-mcp-hint.md").exists()
    assert (repo / ".codex" / "instructions.md").exists()
    assert (repo / ".cursor" / "mcp.json").exists()
    assert (repo / ".cursor" / "rules" / "rekipedia.mdc").exists()
