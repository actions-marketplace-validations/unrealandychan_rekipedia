"""Tests for D3.js graph visualization endpoints (#47)."""
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
        app = create_app(
            repo_root=repo,
            output_dir=output_dir,
            llm_config=LLMConfig(provider="openai", model="gpt-4o-mini", api_key="test"),
        )
        yield TestClient(app)


def test_graph_page_returns_200(client):
    resp = client.get("/graph")
    assert resp.status_code == 200
    assert "html" in resp.headers["content-type"].lower() or resp.text.strip().startswith("<!") or "<" in resp.text


def test_api_graph_data_structure(client):
    resp = client.get("/api/graph-data")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


def test_api_graph_data_edge_fields(client):
    """If any edges are returned, they should have source/target/kind."""
    resp = client.get("/api/graph-data")
    assert resp.status_code == 200
    data = resp.json()
    for edge in data["edges"]:
        assert "source" in edge
        assert "target" in edge
        assert "kind" in edge
