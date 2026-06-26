# tests/test_log_md.py
"""Tests for wiki changelog log.md generation."""
from pathlib import Path

from rekipedia.exporters.markdown_export import MarkdownExporter


def test_log_md_created_on_export(tmp_path):
    """log.md is created by MarkdownExporter.export()."""
    exporter = MarkdownExporter(tmp_path)
    exporter.export(
        pages={"core": ("Core Module", "# Core\n\nContent.")},
        diagrams={},
        run_id="run_test_001",
    )
    log_path = tmp_path / "wiki" / "log.md"
    assert log_path.exists(), "log.md should be created by export()"
    content = log_path.read_text()
    assert "run_test_001" in content
    assert "core" in content


def test_log_md_has_header(tmp_path):
    """log.md starts with # Wiki Changelog header."""
    exporter = MarkdownExporter(tmp_path)
    exporter.export(pages={"api": ("API", "# API\n")}, diagrams={}, run_id="run_001")
    log_path = tmp_path / "wiki" / "log.md"
    content = log_path.read_text()
    assert content.startswith("# Wiki Changelog")


def test_log_md_appends_on_second_export(tmp_path):
    """Second export prepends a new entry, preserving previous entries."""
    exporter = MarkdownExporter(tmp_path)
    exporter.export(pages={"core": ("Core", "# Core\n")}, diagrams={}, run_id="run_001")
    exporter.export(pages={"api": ("API", "# API\n")}, diagrams={}, run_id="run_002")
    log_path = tmp_path / "wiki" / "log.md"
    content = log_path.read_text()
    assert "run_001" in content
    assert "run_002" in content
    # Newest entry (run_002) should appear before older entry (run_001)
    assert content.index("run_002") < content.index("run_001")


def test_log_md_no_run_id(tmp_path):
    """export() without run_id still writes log.md with 'unknown'."""
    exporter = MarkdownExporter(tmp_path)
    exporter.export(pages={"misc": ("Misc", "# Misc\n")}, diagrams={})
    log_path = tmp_path / "wiki" / "log.md"
    assert log_path.exists()
    assert "unknown" in log_path.read_text()


def test_log_md_page_count(tmp_path):
    """log.md entry records the correct page count."""
    exporter = MarkdownExporter(tmp_path)
    exporter.export(
        pages={
            "a": ("A", "# A\n"),
            "b": ("B", "# B\n"),
            "c": ("C", "# C\n"),
        },
        diagrams={},
        run_id="run_cnt",
    )
    content = (tmp_path / "wiki" / "log.md").read_text()
    assert "3" in content  # 3 pages updated
