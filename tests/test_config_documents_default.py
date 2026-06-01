"""Tests for documents section in default config."""
from __future__ import annotations
from pathlib import Path
import tempfile

from rekipedia.config.loader import load_config, _DEFAULT_CONFIG


def test_default_config_has_documents_section():
    assert "documents" in _DEFAULT_CONFIG
    doc_cfg = _DEFAULT_CONFIG["documents"]
    assert "enabled" in doc_cfg
    assert doc_cfg["enabled"] is False  # opt-in
    assert "extensions" in doc_cfg
    assert ".pdf" in doc_cfg["extensions"]


def test_load_config_includes_documents_defaults(tmp_path):
    """load_config returns documents defaults even when no config.yml exists."""
    cfg = load_config(tmp_path)
    assert "documents" in cfg
    assert cfg["documents"]["enabled"] is False


def test_local_config_overrides_documents_enabled(tmp_path):
    """Local config.yml can override documents.enabled."""
    reki_dir = tmp_path / ".rekipedia"
    reki_dir.mkdir()
    (reki_dir / "config.yml").write_text("documents:\n  enabled: true\n")

    cfg = load_config(tmp_path)
    assert cfg["documents"]["enabled"] is True
    # Other defaults still present
    assert "extensions" in cfg["documents"]


def test_deep_merge_preserves_other_doc_settings(tmp_path):
    """Partial override preserves other document defaults."""
    reki_dir = tmp_path / ".rekipedia"
    reki_dir.mkdir()
    (reki_dir / "config.yml").write_text("documents:\n  max_file_size_mb: 100\n")

    cfg = load_config(tmp_path)
    assert cfg["documents"]["max_file_size_mb"] == 100
    assert cfg["documents"]["enabled"] is False  # default preserved
