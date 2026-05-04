"""Tests for YAML frontmatter in generated wiki pages (Issue #36)."""
from __future__ import annotations

import re

import yaml

from rekipedia.synthesis.page_builder import _ensure_frontmatter


def _make_content(slug="test-page", title="Test Page", body="# Test Page\n\nHello world.\n", **kw):
    return _ensure_frontmatter(slug, title, body, **kw)


def test_page_has_yaml_frontmatter():
    """Generated page content must start with ---."""
    content = _make_content()
    assert content.startswith("---"), "Page content must begin with YAML frontmatter delimiter '---'"


def test_frontmatter_has_required_fields():
    """Frontmatter must contain title, created_at, and rekipedia_version."""
    content = _make_content()
    fm_text = re.match(r"^---\n(.*?)\n---", content, re.DOTALL).group(1)
    data = yaml.safe_load(fm_text)
    assert "title" in data, "Frontmatter missing 'title'"
    assert "created_at" in data, "Frontmatter missing 'created_at'"
    assert "rekipedia_version" in data, "Frontmatter missing 'rekipedia_version'"


def test_frontmatter_is_valid_yaml():
    """Frontmatter block must be parseable by yaml.safe_load."""
    content = _make_content(slug="arch", title="Architecture")
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert m is not None, "Could not locate frontmatter block"
    data = yaml.safe_load(m.group(1))
    assert isinstance(data, dict), "Parsed frontmatter must be a dict"
    assert data["slug"] == "arch"
    assert data["title"] == "Architecture"


def test_frontmatter_importance_field():
    """Frontmatter must contain an importance field; defaults to 50."""
    content_default = _make_content()
    m = re.match(r"^---\n(.*?)\n---", content_default, re.DOTALL)
    data = yaml.safe_load(m.group(1))
    assert "importance" in data, "Frontmatter missing 'importance'"
    assert data["importance"] == 50, "Default importance should be 50"

    content_custom = _make_content(importance=80)
    m2 = re.match(r"^---\n(.*?)\n---", content_custom, re.DOTALL)
    data2 = yaml.safe_load(m2.group(1))
    assert data2["importance"] == 80, "Custom importance not reflected in frontmatter"


def test_frontmatter_section_field():
    """Frontmatter must contain a section field; defaults to 'general'."""
    content = _make_content()
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    data = yaml.safe_load(m.group(1))
    assert "section" in data, "Frontmatter missing 'section'"
    assert data["section"] == "general"

    content_sec = _make_content(section="infrastructure")
    m2 = re.match(r"^---\n(.*?)\n---", content_sec, re.DOTALL)
    data2 = yaml.safe_load(m2.group(1))
    assert data2["section"] == "infrastructure"


def test_existing_frontmatter_not_duplicated():
    """Content already starting with --- must not get a second frontmatter block."""
    already = "---\nslug: existing\ntitle: Already\n---\n\n# Already\n"
    result = _ensure_frontmatter("existing", "Already", already)
    assert result.count("---") == 2, "Should not duplicate existing frontmatter delimiters"
    assert result == already
