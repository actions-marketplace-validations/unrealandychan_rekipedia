"""Tests for DocumentExtractor (liteparse optional dep)."""
from __future__ import annotations
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rekipedia.extractors.document_extractor import (
    DocumentChunk,
    DocumentExtractor,
    SUPPORTED_EXTENSIONS,
)


def test_supported_extensions():
    assert ".pdf" in SUPPORTED_EXTENSIONS
    assert ".docx" in SUPPORTED_EXTENSIONS
    assert ".pptx" in SUPPORTED_EXTENSIONS
    assert ".xlsx" in SUPPORTED_EXTENSIONS


def test_extractor_supports_pdf(tmp_path):
    extractor = DocumentExtractor()
    fake_pdf = tmp_path / "report.pdf"
    fake_pdf.touch()
    assert extractor.supports(fake_pdf) is True


def test_extractor_rejects_python(tmp_path):
    extractor = DocumentExtractor()
    py = tmp_path / "script.py"
    py.touch()
    assert extractor.supports(py) is False


def test_extract_returns_empty_when_liteparse_missing(tmp_path):
    """When liteparse is not installed, extract() should return [] gracefully."""
    extractor = DocumentExtractor()
    extractor._available = None  # reset cache
    fake_pdf = tmp_path / "file.pdf"
    fake_pdf.write_bytes(b"%PDF fake")

    with patch.dict(sys.modules, {"liteparse": None}):
        # Force reimport check
        extractor._available = None
        result = extractor.extract(fake_pdf)
    assert result == []


def test_extract_with_mock_liteparse(tmp_path):
    """With a mocked liteparse, extract() should return DocumentChunks."""
    fake_pdf = tmp_path / "doc.pdf"
    fake_pdf.write_bytes(b"%PDF fake")

    mock_liteparse = MagicMock()
    mock_liteparse.parse.return_value = [
        {"text": "Hello world", "blocks": []},
        {"text": "Page two content", "blocks": []},
    ]

    extractor = DocumentExtractor()
    extractor._available = True  # skip availability check

    with patch.dict(sys.modules, {"liteparse": mock_liteparse}):
        chunks = extractor.extract(fake_pdf)

    assert len(chunks) == 2
    assert chunks[0].page_number == 1
    assert chunks[0].text == "Hello world"
    assert chunks[1].page_number == 2


def test_extract_with_blocks(tmp_path):
    """Blocks are extracted individually."""
    fake_pdf = tmp_path / "doc.pdf"
    fake_pdf.write_bytes(b"%PDF fake")

    mock_liteparse = MagicMock()
    mock_liteparse.parse.return_value = [
        {
            "text": "ignored",
            "blocks": [
                {"text": "Block A", "x": 10, "y": 20, "w": 100, "h": 15},
                {"text": "Block B", "x": 10, "y": 40, "w": 100, "h": 15},
            ],
        }
    ]

    extractor = DocumentExtractor()
    extractor._available = True

    with patch.dict(sys.modules, {"liteparse": mock_liteparse}):
        chunks = extractor.extract(fake_pdf)

    assert len(chunks) == 2
    assert chunks[0].text == "Block A"
    assert chunks[0].bounding_box == {"x": 10, "y": 20, "w": 100, "h": 15}


def test_extract_missing_file(tmp_path):
    """Missing files return empty list without raising."""
    extractor = DocumentExtractor()
    extractor._available = True
    result = extractor.extract(tmp_path / "nonexistent.pdf")
    assert result == []


def test_extract_handles_exception(tmp_path, caplog):
    """Parse exceptions are caught and logged as warnings."""
    fake_pdf = tmp_path / "broken.pdf"
    fake_pdf.write_bytes(b"broken")

    mock_liteparse = MagicMock()
    mock_liteparse.parse.side_effect = ValueError("corrupt file")

    extractor = DocumentExtractor()
    extractor._available = True

    import logging
    with patch.dict(sys.modules, {"liteparse": mock_liteparse}):
        with caplog.at_level(logging.WARNING, logger="rekipedia.extractors.document_extractor"):
            result = extractor.extract(fake_pdf)

    assert result == []
    assert "broken.pdf" in caplog.text
