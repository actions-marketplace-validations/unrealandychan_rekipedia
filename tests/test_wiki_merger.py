"""Tests for semantic wiki page merging during scan."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from rekipedia.exporters.markdown_export import MarkdownExporter
from rekipedia.synthesis.merger import merge_wiki_pages


def test_merge_wiki_pages_success():
    # Setup mock LLM response
    mock_llm = MagicMock()
    mock_llm.call.return_value = """---
slug: onboarding
title: "Onboarding"
---

# Onboarding

**Merged Custom Content**
"""

    existing = "# Onboarding\n\nManual developer notes."
    new_doc = "# Onboarding\n\nNew static documentation."

    merged = merge_wiki_pages(mock_llm, "onboarding", existing, new_doc)
    assert "Merged Custom Content" in merged


def test_markdown_exporter_with_merger(tmp_path):
    mock_llm = MagicMock()
    mock_llm.call.return_value = "# Merged Output"

    exporter = MarkdownExporter(tmp_path, llm_client=mock_llm)
    
    # 1. Write an existing file
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    existing_file = wiki_dir / "index.md"
    existing_file.write_text("# Existing index page", encoding="utf-8")

    # 2. Export new pages
    pages = {"index": ("Index", "# New index page")}
    exporter.export(pages, {})

    # The file should be merged
    assert existing_file.read_text(encoding="utf-8") == "# Merged Output"
