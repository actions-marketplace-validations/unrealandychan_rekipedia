"""Export wiki pages and diagrams as Markdown files."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class MarkdownExporter:
    def __init__(self, output_dir: Path, llm_client: Any = None) -> None:
        self._wiki_dir = output_dir / "wiki"
        self._diagram_dir = output_dir / "diagrams"
        self._llm_client = llm_client

    def export(
        self,
        pages: dict[str, tuple[str, str]],
        diagrams: dict[str, tuple[str, str]],
        run_id: str | None = None,
        store: Any = None,
    ) -> None:
        """Write pages to `wiki/` and diagrams to `diagrams/`.

        Args:
            pages: {slug: (title, markdown_content)}
            diagrams: {name: (diagram_type, mermaid_content)}
            run_id: Optional scan run ID to track revisions
            store: Optional SqliteStore instance to track revisions
        """
        self._wiki_dir.mkdir(parents=True, exist_ok=True)
        self._diagram_dir.mkdir(parents=True, exist_ok=True)

        for slug, (_title, content) in pages.items():
            out = self._wiki_dir / f"{slug}.md"
            # Never overwrite a pinned page
            if out.exists() and _is_pinned(out):
                continue

            # Semantically merge if the file exists and we have an llm_client
            if out.exists() and self._llm_client:
                from rekipedia.synthesis.merger import merge_wiki_pages
                existing_content = out.read_text(encoding="utf-8")
                content = merge_wiki_pages(self._llm_client, slug, existing_content, content)

            out.write_text(content, encoding="utf-8")

            # Save revision if store and run_id are provided
            if store and run_id:
                try:
                    store.upsert_wiki_revision(slug, run_id, _title, content)
                except Exception:
                    pass

        for name, (_dtype, content) in diagrams.items():
            out = self._diagram_dir / f"{name}.md"
            out.write_text(f"```mermaid\n{content}\n```\n", encoding="utf-8")

        # Write wiki changelog entry (OKF log.md pattern)
        _write_log_entry(self._wiki_dir, run_id, pages)


def _is_pinned(path: Path) -> bool:
    import re
    text = path.read_text(encoding="utf-8")
    return bool(re.search(r"^pin:\s*true", text, re.MULTILINE))


def _write_log_entry(wiki_dir: Path, run_id: str | None, pages: dict) -> None:
    """Append a changelog entry to wiki/log.md (OKF §7 pattern).

    Newest entry is prepended. File created if it doesn't exist.

    Args:
        wiki_dir: Path to the .rekipedia/wiki/ directory.
        run_id: Current scan run ID, or None.
        pages: Dict of {slug: (title, content)} pages written this run.
    """
    log_path = wiki_dir / "log.md"
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    run_label = run_id or "unknown"
    new_pages = sorted(pages.keys())
    page_list = "\n".join(f"  - `{slug}`" for slug in new_pages)
    entry = (
        f"## {now} (run: `{run_label}`)\n\n"
        f"- Pages updated: {len(new_pages)}\n"
        f"{page_list}\n\n"
    )

    if log_path.exists():
        existing = log_path.read_text(encoding="utf-8")
        if existing.startswith("# Wiki Changelog"):
            header, rest = existing.split("\n", 1)
            log_path.write_text(f"{header}\n\n{entry}{rest.lstrip()}", encoding="utf-8")
        else:
            log_path.write_text(entry + existing, encoding="utf-8")
    else:
        log_path.write_text(f"# Wiki Changelog\n\n{entry}", encoding="utf-8")
