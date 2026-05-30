"""Tests for list_wiki_pages and get_wiki_page MCP tools."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from rekipedia.cli.mcp_server import _handle_tool, _StoreCache


class _NoDBCache(_StoreCache):
    """Cache that reports available=True but has no real DB (for wiki-only tests)."""

    def __init__(self):
        pass  # skip real init

    @property
    def available(self):
        return True


@pytest.fixture()
def cache():
    return _NoDBCache()


def test_list_wiki_pages_empty(tmp_path: Path, cache):
    result = json.loads(_handle_tool("list_wiki_pages", {"repo": str(tmp_path)}, cache))
    assert result == {"pages": []}


def test_list_wiki_pages_rekipedia_dir(tmp_path: Path, cache):
    wiki_dir = tmp_path / ".rekipedia" / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "overview.md").write_text("# Overview")
    (wiki_dir / "auth.md").write_text("# Auth")

    result = json.loads(_handle_tool("list_wiki_pages", {"repo": str(tmp_path)}, cache))
    names = [p["name"] for p in result["pages"]]
    assert "overview" in names
    assert "auth" in names
    assert names == sorted(names)


def test_list_wiki_pages_docs_dir(tmp_path: Path, cache):
    wiki_dir = tmp_path / "docs" / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "mypage.md").write_text("# My Page")

    result = json.loads(_handle_tool("list_wiki_pages", {"repo": str(tmp_path)}, cache))
    names = [p["name"] for p in result["pages"]]
    assert "mypage" in names


def test_get_wiki_page_found(tmp_path: Path, cache):
    wiki_dir = tmp_path / ".rekipedia" / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "authentication.md").write_text("# Auth content")

    result = json.loads(_handle_tool("get_wiki_page", {"page": "auth", "repo": str(tmp_path)}, cache))
    assert result["page"] == "authentication"
    assert "Auth content" in result["content"]


def test_get_wiki_page_not_found(tmp_path: Path, cache):
    wiki_dir = tmp_path / ".rekipedia" / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "overview.md").write_text("# Overview")

    result = json.loads(_handle_tool("get_wiki_page", {"page": "nonexistent", "repo": str(tmp_path)}, cache))
    assert result["error"] == "Page not found"
    assert "overview" in result["available"]


def test_get_wiki_page_case_insensitive(tmp_path: Path, cache):
    wiki_dir = tmp_path / ".rekipedia" / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "DataModels.md").write_text("# Data Models")

    result = json.loads(_handle_tool("get_wiki_page", {"page": "datamodels", "repo": str(tmp_path)}, cache))
    assert result["page"] == "DataModels"
