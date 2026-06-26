# tests/test_section_index.py
"""Tests for per-section index.md generation (OKF §6 progressive disclosure)."""
from pathlib import Path

import yaml


def test_section_index_written(tmp_path):
    """Section indexes are written for each unique section."""
    from rekipedia.exporters.section_index import write_section_indexes

    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    pages_meta = [
        {"slug": "architecture", "title": "Architecture", "section": "internals", "tags": ["arch"]},
        {"slug": "data-flow",    "title": "Data Flow",    "section": "internals", "tags": []},
        {"slug": "cli-ref",      "title": "CLI Reference","section": "api",       "tags": ["cli"]},
        {"slug": "index",        "title": "Index",        "section": "",          "tags": []},
    ]

    result = write_section_indexes(wiki_dir, pages_meta)

    internals_idx = wiki_dir / "index-internals.md"
    api_idx = wiki_dir / "index-api.md"
    assert internals_idx.exists(), "should write index-internals.md"
    assert api_idx.exists(), "should write index-api.md"
    assert not (wiki_dir / "index-.md").exists(), "no index for empty section"

    internals_content = internals_idx.read_text()
    assert "Architecture" in internals_content
    assert "Data Flow" in internals_content
    assert "architecture.md" in internals_content
    assert "data-flow.md" in internals_content

    assert result["sections"] == {"internals": 2, "api": 1}


def test_section_index_okf_frontmatter(tmp_path):
    """Section index files have valid OKF-compatible frontmatter."""
    from rekipedia.exporters.section_index import write_section_indexes

    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    pages_meta = [
        {"slug": "auth", "title": "Auth", "section": "security", "tags": ["security"]},
    ]
    write_section_indexes(wiki_dir, pages_meta)

    content = (wiki_dir / "index-security.md").read_text()
    # Parse frontmatter
    end = content.find("\n---", 3)
    fm = yaml.safe_load(content[3:end])
    assert fm["type"] == "rekipedia/section-index"
    assert fm["title"] == "Security"
    assert "security" in fm["tags"]
    assert "1" in fm["description"]


def test_no_section_no_index(tmp_path):
    """No index files written when all pages lack section metadata."""
    from rekipedia.exporters.section_index import write_section_indexes

    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    pages_meta = [
        {"slug": "misc", "title": "Misc", "section": "", "tags": []},
        {"slug": "other", "title": "Other"},  # no section key at all
    ]
    result = write_section_indexes(wiki_dir, pages_meta)
    assert result["sections"] == {}
    assert list(wiki_dir.glob("index-*.md")) == []


def test_section_index_sorted_pages(tmp_path):
    """Pages within a section index are sorted alphabetically by title."""
    from rekipedia.exporters.section_index import write_section_indexes

    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    pages_meta = [
        {"slug": "zebra", "title": "Zebra", "section": "animals", "tags": []},
        {"slug": "aardvark", "title": "Aardvark", "section": "animals", "tags": []},
        {"slug": "monkey", "title": "Monkey", "section": "animals", "tags": []},
    ]
    write_section_indexes(wiki_dir, pages_meta)
    content = (wiki_dir / "index-animals.md").read_text()
    aardvark_pos = content.index("Aardvark")
    monkey_pos = content.index("Monkey")
    zebra_pos = content.index("Zebra")
    assert aardvark_pos < monkey_pos < zebra_pos


def test_markdown_exporter_no_crash_without_section(tmp_path):
    """MarkdownExporter.export() does not crash when pages have no section metadata."""
    from rekipedia.exporters.markdown_export import MarkdownExporter

    exporter = MarkdownExporter(tmp_path)
    # No exception expected
    exporter.export(
        pages={"core": ("Core Module", "# Core\n\nContent.")},
        diagrams={},
        run_id="run_001",
    )
    assert (tmp_path / "wiki" / "core.md").exists()
