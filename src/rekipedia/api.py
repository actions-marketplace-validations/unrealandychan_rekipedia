"""rekipedia Python API — programmatic interface for scan and ask.

Quick start::

    import rekipedia

    # Scan a local repo
    result = rekipedia.scan("/path/to/repo")
    print(result.page_count, result.symbol_count)

    # Ask a question (grounded, with citations)
    answer = rekipedia.ask("/path/to/repo", "How does the auth flow work?")
    print(answer.text)
    for c in answer.citations:
        print(c.file, c.line)

    # Async variants
    result = await rekipedia.scan_async("/path/to/repo")
    answer = await rekipedia.ask_async("/path/to/repo", "...")
"""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "scan",
    "scan_async",
    "ask",
    "ask_async",
    "ScanResult",
    "AskResult",
    "Citation",
]


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


@dataclass
class ScanResult:
    """Result returned by :func:`scan` / :func:`scan_async`."""

    repo_path: Path
    """Absolute path to the scanned repository."""

    db_path: Path
    """Path to the SQLite knowledge store (``<repo>/.rekipedia/store.db``)."""

    wiki_dir: Path
    """Path to the generated wiki directory (``<repo>/.rekipedia/wiki/``)."""

    page_count: int = 0
    """Number of wiki pages generated."""

    symbol_count: int = 0
    """Number of code symbols extracted."""

    token_count: int = 0
    """Estimated token count of the wiki (approximate, chars / 4)."""

    wiki_pages: list[dict[str, Any]] = field(default_factory=list)
    """List of wiki page metadata dicts (``{slug, title, path}``)."""

    run_id: str = ""
    """Internal scan run ID stored in the knowledge store."""

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ScanResult repo={self.repo_path.name!r} "
            f"pages={self.page_count} symbols={self.symbol_count} "
            f"tokens≈{self.token_count}>"
        )


@dataclass
class Citation:
    """A single source citation returned inside an :class:`AskResult`."""

    file: str
    """Relative file path (e.g. ``src/rekipedia/api.py``)."""

    line: int | None = None
    """Line number, if parseable from the citation text."""

    snippet: str = ""
    """Short excerpt from the source."""


@dataclass
class AskResult:
    """Result returned by :func:`ask` / :func:`ask_async`."""

    question: str
    """The original question."""

    text: str
    """The LLM-generated answer, grounded in the scanned codebase."""

    citations: list[Citation] = field(default_factory=list)
    """Source citations extracted from the answer."""

    model_used: str = ""
    """LLM model string that produced the answer."""

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AskResult question={self.question!r} citations={len(self.citations)}>"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_CITE_RE = re.compile(
    r"`?([^\s`]+\.(?:py|ts|js|go|java|rs|cpp|c|h|md))`?"
    r"(?::(\d+))?",
    re.IGNORECASE,
)


def _parse_citations(text: str) -> list[Citation]:
    """Extract file:line citations from an LLM answer."""
    seen: set[str] = set()
    citations: list[Citation] = []
    for m in _CITE_RE.finditer(text):
        file = m.group(1)
        line_str = m.group(2)
        key = f"{file}:{line_str}"
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            Citation(
                file=file,
                line=int(line_str) if line_str else None,
            )
        )
    return citations


def _resolve_output_dir(repo_path: Path) -> Path:
    return repo_path / ".rekipedia"


def _collect_wiki_pages(wiki_dir: Path) -> list[dict[str, Any]]:
    if not wiki_dir.exists():
        return []
    pages = []
    for md in sorted(wiki_dir.glob("*.md")):
        slug = md.stem
        title = slug.replace("-", " ").replace("_", " ").title()
        # Try to read title from frontmatter
        try:
            raw = md.read_text(errors="replace")
            if raw.startswith("---"):
                end = raw.find("\n---", 3)
                if end != -1:
                    for line in raw[3:end].splitlines():
                        if line.startswith("title:"):
                            title = line.split(":", 1)[1].strip().strip("\"'")
                            break
        except OSError:
            pass
        pages.append({"slug": slug, "title": title, "path": str(md)})
    return pages


def _count_tokens(wiki_dir: Path) -> int:
    """Rough token estimate: total chars / 4."""
    if not wiki_dir.exists():
        return 0
    total = sum(
        len(md.read_text(errors="replace"))
        for md in wiki_dir.glob("*.md")
    )
    return total // 4


def _count_symbols(output_dir: Path) -> int:
    symbols_json = output_dir / "exports" / "symbols.json"
    if not symbols_json.exists():
        return 0
    try:
        data = json.loads(symbols_json.read_text())
        return len(data) if isinstance(data, list) else 0
    except (json.JSONDecodeError, OSError):
        return 0


def _get_run_id(output_dir: Path) -> str:
    try:
        from rekipedia.storage.sqlite_store import SqliteStore

        store = SqliteStore(output_dir / "store.db")
        return store.get_latest_run_id(str(output_dir.parent)) or ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Public sync API
# ---------------------------------------------------------------------------


def scan(
    repo_path: str | Path,
    *,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    force: bool = False,
    languages: list[str] | None = None,
) -> ScanResult:
    """Scan a local repository and build the rekipedia knowledge store.

    Parameters
    ----------
    repo_path:
        Path to the repository root (must be a local directory).
    model:
        LLM model string (e.g. ``"gpt-4o"``, ``"ollama/llama3"``).
        Defaults to the value in ``.rekipedia/config.yml`` or the
        ``REKIPEDIA_MODEL`` environment variable.
    api_key:
        LLM API key. Falls back to ``REKIPEDIA_API_KEY`` / ``OPENAI_API_KEY``.
    base_url:
        Custom LLM base URL for self-hosted endpoints.
    force:
        Re-scan even if a successful scan already exists in the store.
    languages:
        List of languages to scan (e.g. ``["python", "typescript"]``).
        ``None`` scans all supported languages.

    Returns
    -------
    ScanResult
        Structured result with page/symbol counts and paths.
    """
    from rekipedia.models.contracts import LLMConfig
    from rekipedia.orchestrator.run_digest import run_digest

    repo = Path(repo_path).resolve()
    output_dir = _resolve_output_dir(repo)
    output_dir.mkdir(parents=True, exist_ok=True)

    llm_cfg = LLMConfig(
        model=model or "",
        api_key=api_key or "",
        base_url=base_url or "",
    )

    run_digest(
        repo_root=repo,
        output_dir=output_dir,
        llm_config=llm_cfg,
        force=force,
        languages=languages,
        progress=None,
    )

    wiki_dir = output_dir / "wiki"
    pages = _collect_wiki_pages(wiki_dir)

    return ScanResult(
        repo_path=repo,
        db_path=output_dir / "store.db",
        wiki_dir=wiki_dir,
        page_count=len(pages),
        symbol_count=_count_symbols(output_dir),
        token_count=_count_tokens(wiki_dir),
        wiki_pages=pages,
        run_id=_get_run_id(output_dir),
    )


def ask(
    repo_path: str | Path,
    question: str,
    *,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> AskResult:
    """Ask a question about a scanned repository.

    The repository must have been scanned first (via :func:`scan` or
    ``reki scan``).

    Parameters
    ----------
    repo_path:
        Path to the repository root.
    question:
        Natural-language question about the codebase.
    model:
        LLM model string. Falls back to config / env vars.
    api_key:
        LLM API key. Falls back to ``REKIPEDIA_API_KEY`` / ``OPENAI_API_KEY``.
    base_url:
        Custom LLM base URL.

    Returns
    -------
    AskResult
        Answer text with parsed citations and model info.
    """
    from rekipedia.models.contracts import LLMConfig
    from rekipedia.orchestrator.run_ask import run_ask

    repo = Path(repo_path).resolve()
    output_dir = _resolve_output_dir(repo)

    llm_cfg = LLMConfig(
        model=model or "",
        api_key=api_key or "",
        base_url=base_url or "",
    )

    answer_text = run_ask(
        question=question,
        repo_root=repo,
        output_dir=output_dir,
        llm_config=llm_cfg,
    )

    return AskResult(
        question=question,
        text=answer_text,
        citations=_parse_citations(answer_text),
        model_used=llm_cfg.model,
    )


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------


async def scan_async(
    repo_path: str | Path,
    *,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    force: bool = False,
    languages: list[str] | None = None,
) -> ScanResult:
    """Async variant of :func:`scan`. Runs in a thread pool."""
    return await asyncio.to_thread(
        scan,
        repo_path,
        model=model,
        api_key=api_key,
        base_url=base_url,
        force=force,
        languages=languages,
    )


async def ask_async(
    repo_path: str | Path,
    question: str,
    *,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> AskResult:
    """Async variant of :func:`ask`. Runs in a thread pool."""
    return await asyncio.to_thread(
        ask,
        repo_path,
        question,
        model=model,
        api_key=api_key,
        base_url=base_url,
    )
