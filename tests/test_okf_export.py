# tests/test_okf_export.py
"""Tests for OKF (Open Knowledge Format) exporter."""
from pathlib import Path

import pytest
import yaml


def test_okf_frontmatter_mapping():
    """Verify rekipedia page metadata maps correctly to OKF frontmatter."""
    from rekipedia.exporters.okf_export import _to_okf_frontmatter

    reki_meta = {
        "slug": "architecture",
        "title": "Architecture",
        "section": "architecture",
        "tags": ["architecture", "internals"],
        "importance": 50,
    }
    fm = _to_okf_frontmatter(reki_meta)
    assert fm["type"] == "rekipedia/wiki-page"
    assert fm["title"] == "Architecture"
    assert fm["description"] == ""  # no description provided
    assert fm["resource"] == "wiki/architecture.md"
    assert fm["tags"] == ["architecture", "internals"]
    assert "timestamp" in fm


def test_okf_frontmatter_default_title():
    """Slug-based title used when title field is missing."""
    from rekipedia.exporters.okf_export import _to_okf_frontmatter

    fm = _to_okf_frontmatter({"slug": "data-flow"})
    assert fm["title"] == "Data Flow"


def test_extract_description():
    """First non-heading line extracted as description."""
    from rekipedia.exporters.okf_export import _extract_description

    body = "# Architecture\n\nThis is the overview paragraph.\n\nMore text."
    assert _extract_description(body) == "This is the overview paragraph."


def test_extract_description_empty():
    """Returns empty string for heading-only body."""
    from rekipedia.exporters.okf_export import _extract_description

    assert _extract_description("# Title\n\n## Sub\n") == ""


def test_strip_reki_frontmatter():
    """Reki frontmatter is split from body correctly."""
    from rekipedia.exporters.okf_export import _strip_reki_frontmatter

    content = '---\nslug: arch\ntitle: "Arch"\ntags: []\n---\n\n# Arch\n\nBody text.\n'
    fm, body = _strip_reki_frontmatter(content)
    assert fm["slug"] == "arch"
    assert fm["title"] == "Arch"
    assert body.startswith("# Arch")


def test_strip_reki_frontmatter_no_fm():
    """Content without frontmatter returns empty dict and full content."""
    from rekipedia.exporters.okf_export import _strip_reki_frontmatter

    content = "# No Frontmatter\n\nJust body."
    fm, body = _strip_reki_frontmatter(content)
    assert fm == {}
    assert body == content


def test_okf_exporter_writes_bundle(tmp_path):
    """Full OKF bundle is written with correct structure and frontmatter."""
    from rekipedia.exporters.okf_export import OkfExporter

    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "architecture.md").write_text(
        '---\nslug: architecture\ntitle: "Architecture"\nsection: internals\ntags:\n  - arch\nimportance: 50\n---\n\n# Architecture\n\nThis is the arch page.\n',
        encoding="utf-8",
    )
    diagrams_dir = tmp_path / "diagrams"
    diagrams_dir.mkdir()
    (diagrams_dir / "module-graph.md").write_text(
        "```mermaid\ngraph TD\n  A-->B\n```\n", encoding="utf-8"
    )

    out_dir = tmp_path / "okf-bundle"
    exporter = OkfExporter(wiki_dir, diagrams_dir, tmp_path)
    result = exporter.export(out_dir)

    # Check structure
    assert (out_dir / "index.md").exists()
    assert (out_dir / "log.md").exists()
    assert (out_dir / "wiki" / "architecture.md").exists()
    assert (out_dir / "diagrams" / "module-graph.md").exists()

    # Check OKF frontmatter on wiki page
    wiki_page = (out_dir / "wiki" / "architecture.md").read_text(encoding="utf-8")
    assert "type: rekipedia/wiki-page" in wiki_page
    assert "title: Architecture" in wiki_page
    assert "resource: wiki/architecture.md" in wiki_page
    assert "# Architecture" in wiki_page

    # Check OKF frontmatter on diagram
    diag_page = (out_dir / "diagrams" / "module-graph.md").read_text(encoding="utf-8")
    assert "type: rekipedia/diagram" in diag_page

    # Check index.md lists the page
    index_content = (out_dir / "index.md").read_text(encoding="utf-8")
    assert "Architecture" in index_content
    assert "wiki/architecture.md" in index_content
    assert "Module Graph" in index_content

    # Check log.md exists and has an entry
    log_content = (out_dir / "log.md").read_text(encoding="utf-8")
    assert "Knowledge Bundle Changelog" in log_content
    assert "1 wiki pages" in log_content

    # Check result summary
    assert result["pages"] == ["architecture"]
    assert result["diagrams"] == ["module-graph"]


def test_okf_exporter_log_appends(tmp_path):
    """Second export prepends a new log entry, preserving old entries."""
    from rekipedia.exporters.okf_export import OkfExporter

    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "core.md").write_text("# Core\n\nContent.\n", encoding="utf-8")
    diagrams_dir = tmp_path / "diagrams"
    diagrams_dir.mkdir()

    out_dir = tmp_path / "okf-bundle"
    exporter = OkfExporter(wiki_dir, diagrams_dir, tmp_path)
    exporter.export(out_dir)
    exporter.export(out_dir)

    log_content = (out_dir / "log.md").read_text(encoding="utf-8")
    # Should have two entries — count "OKF bundle exported" occurrences
    assert log_content.count("OKF bundle exported") == 2


def test_export_okf_cli(tmp_path):
    """CLI --format okf produces bundle and prints confirmation."""
    from click.testing import CliRunner
    from rekipedia.cli.export import export_cmd

    wiki_dir = tmp_path / ".rekipedia" / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "index.md").write_text(
        '---\nslug: index\ntitle: "Index"\ntags: []\n---\n\n# Index\n\nOverview.\n',
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(export_cmd, [str(tmp_path), "--format", "okf"])
    assert result.exit_code == 0, result.output
    assert "OKF bundle exported" in result.output

    bundle_dir = tmp_path / ".rekipedia" / "okf-bundle"
    assert (bundle_dir / "index.md").exists()
    assert (bundle_dir / "wiki" / "index.md").exists()
    assert (bundle_dir / "log.md").exists()
