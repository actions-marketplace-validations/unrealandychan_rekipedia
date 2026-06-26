# tests/test_serve_branding.py
"""Tests for reki serve --title / --logo branding options."""
from pathlib import Path

import pytest


def _make_app(tmp_path: Path, title=None, logo=None):
    from rekipedia.models.contracts import LLMConfig
    from rekipedia.server.app import create_app

    llm = LLMConfig(model="ollama/llama3", api_key="", base_url="", temperature=0.2)
    return create_app(
        repo_root=tmp_path,
        output_dir=tmp_path / ".rekipedia",
        llm_config=llm,
        custom_title=title,
        custom_logo=logo,
    )


def test_api_config_default_title(tmp_path):
    """Without --title, /api/config returns repo name as title."""
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    # title = repo name (tmp dir name), has_logo = False
    assert "title" in data
    assert data["has_logo"] is False


def test_api_config_custom_title(tmp_path):
    """--title is reflected in /api/config."""
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path, title="My Awesome Project")
    client = TestClient(app)
    resp = client.get("/api/config")
    assert resp.status_code == 200
    assert resp.json()["title"] == "My Awesome Project"


def test_api_config_logo_present(tmp_path):
    """When a valid logo path is passed, has_logo is True."""
    from fastapi.testclient import TestClient

    logo = tmp_path / "logo.png"
    logo.write_bytes(b"\x89PNG\r\n")
    app = _make_app(tmp_path, logo=logo)
    client = TestClient(app)
    resp = client.get("/api/config")
    assert resp.status_code == 200
    assert resp.json()["has_logo"] is True


def test_logo_endpoint_serves_file(tmp_path):
    """/logo returns the image bytes with correct content-type."""
    from fastapi.testclient import TestClient

    logo = tmp_path / "brand.png"
    logo.write_bytes(b"\x89PNG\r\n\x1a\n")
    app = _make_app(tmp_path, logo=logo)
    client = TestClient(app)
    resp = client.get("/logo")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content[:4] == b"\x89PNG"


def test_logo_endpoint_404_when_not_configured(tmp_path):
    """/logo returns 404 when no logo was configured."""
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)
    resp = client.get("/logo")
    assert resp.status_code == 404


def test_logo_svg_content_type(tmp_path):
    """/logo returns image/svg+xml for .svg files."""
    from fastapi.testclient import TestClient

    logo = tmp_path / "icon.svg"
    logo.write_text("<svg/>")
    app = _make_app(tmp_path, logo=logo)
    client = TestClient(app)
    resp = client.get("/logo")
    assert resp.status_code == 200
    assert "svg" in resp.headers["content-type"]


def test_fastapi_app_title_set(tmp_path):
    """FastAPI app.title is set to custom_title."""
    app = _make_app(tmp_path, title="Demo Title")
    assert app.title == "Demo Title"


def test_fastapi_app_title_default(tmp_path):
    """FastAPI app.title falls back to 'rekipedia' when no custom title."""
    app = _make_app(tmp_path)
    assert app.title == "rekipedia"
