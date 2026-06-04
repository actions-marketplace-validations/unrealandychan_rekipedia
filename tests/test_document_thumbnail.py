"""Tests for DocumentExtractor.thumbnail() — issue #205."""
from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rekipedia.extractors.document_extractor import DocumentExtractor


def _make_extractor(available: bool = True) -> DocumentExtractor:
    ext = DocumentExtractor()
    ext._available = available
    return ext


def test_thumbnail_returns_none_when_unavailable(tmp_path):
    ext = _make_extractor(available=False)
    result = ext.thumbnail(tmp_path / "doc.pdf")
    assert result is None


def test_thumbnail_returns_none_for_non_pdf(tmp_path):
    ext = _make_extractor(available=True)
    result = ext.thumbnail(tmp_path / "doc.docx")
    assert result is None


def test_thumbnail_returns_png_bytes(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    # Create a fake PIL image that returns PNG bytes
    fake_img = MagicMock()
    def save_side_effect(buf, format):
        buf.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
    fake_img.save.side_effect = save_side_effect

    fake_liteparse = MagicMock()
    fake_liteparse.screenshot.return_value = [fake_img]

    ext = _make_extractor(available=True)

    with patch.dict("sys.modules", {"liteparse": fake_liteparse}):
        result = ext.thumbnail(pdf_path, dpi=72)

    assert result is not None
    assert result[:4] == b"\x89PNG"
    fake_liteparse.screenshot.assert_called_once_with(str(pdf_path), pages=[0], dpi=72)


def test_thumbnail_returns_none_when_no_pages(tmp_path):
    pdf_path = tmp_path / "empty.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    fake_liteparse = MagicMock()
    fake_liteparse.screenshot.return_value = []

    ext = _make_extractor(available=True)

    with patch.dict("sys.modules", {"liteparse": fake_liteparse}):
        result = ext.thumbnail(pdf_path)

    assert result is None


def test_thumbnail_returns_none_on_exception(tmp_path):
    pdf_path = tmp_path / "bad.pdf"
    pdf_path.write_bytes(b"not a pdf")

    fake_liteparse = MagicMock()
    fake_liteparse.screenshot.side_effect = RuntimeError("render failed")

    ext = _make_extractor(available=True)

    with patch.dict("sys.modules", {"liteparse": fake_liteparse}):
        result = ext.thumbnail(pdf_path)

    assert result is None
