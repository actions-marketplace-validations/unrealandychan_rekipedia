"""Tests for CI scaffold liteparse auto-detect — issue #206."""
from rekipedia.cli.init import _GH_ACTIONS_TEMPLATE


def test_ci_template_contains_liteparse_detect():
    assert "liteparse" in _GH_ACTIONS_TEMPLATE


def test_ci_template_installs_rekipedia_docs():
    assert 'rekipedia[docs]' in _GH_ACTIONS_TEMPLATE


def test_ci_template_finds_document_files():
    assert 'find . -name "*.pdf"' in _GH_ACTIONS_TEMPLATE


def test_ci_template_has_document_files_message():
    assert "Document files found" in _GH_ACTIONS_TEMPLATE
