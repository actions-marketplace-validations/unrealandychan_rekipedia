"""Document extractor — parse PDF/DOCX/PPTX/XLSX via liteparse (optional dep).

Install: pip install 'rekipedia[docs]'
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("rekipedia.extractors.document_extractor")

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx"}


@dataclass
class DocumentChunk:
    """A single extracted chunk from a document."""
    doc_path: str          # relative path in repo
    page_number: int       # 1-based page number
    text: str              # plain text content
    bounding_box: dict[str, Any] = field(default_factory=dict)  # {x, y, w, h} if available


class DocumentExtractor:
    """Extract text chunks from PDF/DOCX/PPTX/XLSX using liteparse.

    Gracefully degrades: if liteparse is not installed, logs a warning and
    returns empty results instead of raising.
    """

    def __init__(self) -> None:
        self._available: bool | None = None

    def _check_available(self) -> bool:
        if self._available is None:
            try:
                import liteparse  # noqa: F401
                self._available = True
            except ImportError:
                logger.warning(
                    "liteparse not installed — document extraction disabled. "
                    "Install with: pip install 'rekipedia[docs]'"
                )
                self._available = False
        return self._available

    def supports(self, path: Path) -> bool:
        """Return True if this file can be extracted."""
        return path.suffix.lower() in SUPPORTED_EXTENSIONS

    def extract(self, path: Path) -> list[DocumentChunk]:
        """Extract chunks from a document file.

        Returns an empty list if liteparse is unavailable or the file cannot be parsed.
        """
        if not self._check_available():
            return []
        if not path.exists():
            logger.warning("Document not found: %s", path)
            return []

        try:
            import liteparse

            result = liteparse.parse(str(path))
            chunks: list[DocumentChunk] = []

            # liteparse returns a list of page dicts with 'text' and optional 'blocks'
            pages = result if isinstance(result, list) else result.get("pages", [])
            for i, page in enumerate(pages, start=1):
                if isinstance(page, dict):
                    text = page.get("text", "") or ""
                    blocks = page.get("blocks", [])
                else:
                    # Some versions return plain strings
                    text = str(page)
                    blocks = []

                text = text.strip()
                if not text:
                    continue

                if blocks:
                    for block in blocks:
                        block_text = block.get("text", "").strip()
                        if not block_text:
                            continue
                        bbox = {
                            k: block.get(k)
                            for k in ("x", "y", "w", "h")
                            if block.get(k) is not None
                        }
                        chunks.append(DocumentChunk(
                            doc_path=str(path),
                            page_number=i,
                            text=block_text,
                            bounding_box=bbox,
                        ))
                else:
                    chunks.append(DocumentChunk(
                        doc_path=str(path),
                        page_number=i,
                        text=text,
                    ))

            logger.debug("Extracted %d chunks from %s", len(chunks), path)
            return chunks

        except Exception as exc:
            logger.warning("Failed to extract %s: %s", path, exc)
            return []

    def thumbnail(self, path: Path, dpi: int = 150) -> bytes | None:
        """Generate a PNG thumbnail of the first page. Returns raw PNG bytes or None."""
        if not self._check_available():
            return None
        if path.suffix.lower() != ".pdf":
            return None
        try:
            import liteparse
            pages = liteparse.screenshot(str(path), pages=[0], dpi=dpi)
            if pages:
                import io
                buf = io.BytesIO()
                pages[0].save(buf, format="PNG")
                return buf.getvalue()
        except Exception as exc:
            logger.warning("Failed to generate thumbnail for %s: %s", path, exc)
        return None
