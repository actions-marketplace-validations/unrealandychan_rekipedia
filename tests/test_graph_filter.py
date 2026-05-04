"""Tests for graph search/filter functionality (Issue #39)."""
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from rekipedia.models.contracts import LLMConfig
from rekipedia.server.app import create_app
from rekipedia.storage.sqlite_store import SqliteStore


@pytest.fixture
def client():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "myrepo"
        output_dir = repo / ".rekipedia"
        wiki_dir = output_dir / "wiki"
        wiki_dir.mkdir(parents=True)
        (wiki_dir / "index.md").write_text("# Index\n\nHello.")
        db = output_dir / "store.db"
        with SqliteStore(db) as store:
            store.upsert_run("run-1", str(repo))
            store.update_run_status("run-1", "success")
        app = create_app(repo, output_dir, LLMConfig())
        yield TestClient(app, raise_server_exceptions=False)


def test_graph_route_returns_html(client):
    """GET /graph should return 200 HTML."""
    res = client.get("/graph")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")


def test_graph_html_has_search_input(client):
    """Graph page must contain a search input with id='search'."""
    res = client.get("/graph")
    assert res.status_code == 200
    # Accept either id="search" or id="search-box"
    assert 'id="search"' in res.text or 'id="search-box"' in res.text


def test_graph_html_has_filter_js(client):
    """Graph page must contain JS filter logic and Group-by-file button."""
    res = client.get("/graph")
    assert res.status_code == 200
    # Search/filter JS
    assert "searchQ" in res.text or "applySearch" in res.text or "Filter nodes" in res.text
    # Group by file feature
    assert "Group by file" in res.text or "groupByFile" in res.text


def test_graph_html_has_nhop_focus(client):
    """Graph page must contain N-hop focus mode JavaScript."""
    res = client.get("/graph")
    assert res.status_code == 200
    assert "focusedNodeId" in res.text or "N-hop" in res.text or "1-hop" in res.text


def test_graph_data_endpoint_returns_json(client):
    """GET /api/graph should return JSON with nodes and edges keys."""
    res = client.get("/api/graph")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data
