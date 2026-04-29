"""Grounded Q&A pipeline for `close-wiki ask`.

Flow:
    1. Locate the latest successful scan run for this repo.
    2. Load wiki pages from disk (wiki/*.md).
    3. Load symbol index from exports/symbols.json (if present).
    4. Assemble a context string, truncated to a token budget.
    5. Call the LLM with a grounding system prompt.
    6. Return the answer text.
"""
from __future__ import annotations

import json
from pathlib import Path

from close_wiki.llm.client import LLMClient
from close_wiki.models.contracts import LLMConfig
from close_wiki.storage.sqlite_store import SqliteStore

_SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "ask_system.md"

# Approximate character budget for context (≈ 24 K tokens at ~4 chars/token).
# Keeps us safely within the context window of most models.
_CONTEXT_CHAR_BUDGET = 96_000


def run_ask(
    question: str,
    repo_root: Path,
    output_dir: Path,
    llm_config: LLMConfig | None = None,
) -> str:
    """Answer *question* grounded in the knowledge store.

    Args:
        question: Free-text question from the user.
        repo_root: Absolute path to the repository.
        output_dir: `.close-wiki/` directory containing store.db + wiki/.
        llm_config: LLM settings; defaults to LLMConfig().

    Returns:
        The assistant's answer as a Markdown string.

    Raises:
        RuntimeError: If no successful scan exists for the repo.
    """
    llm_config = llm_config or LLMConfig()

    # ── 1. Verify a scan exists ───────────────────────────────────────
    db_path = output_dir / "store.db"
    if not db_path.exists():
        raise RuntimeError(
            f"No knowledge store found at {db_path}.\n"
            "Run `close-wiki scan .` first."
        )

    with SqliteStore(db_path) as store:
        run_id = store.get_latest_run_id(str(repo_root))

    if run_id is None:
        raise RuntimeError(
            "No successful scan found for this repository.\n"
            "Run `close-wiki scan .` first."
        )

    # ── 2. Load wiki pages from disk ──────────────────────────────────
    wiki_dir = output_dir / "wiki"
    page_texts: list[str] = []
    if wiki_dir.exists():
        for md_file in sorted(wiki_dir.glob("*.md")):
            slug = md_file.stem
            content = md_file.read_text(encoding="utf-8")
            page_texts.append(f"## [{slug}.md]\n\n{content}")

    # ── 3. Load symbol index ──────────────────────────────────────────
    symbols_path = output_dir / "exports" / "symbols.json"
    symbol_lines: list[str] = []
    if symbols_path.exists():
        try:
            symbols = json.loads(symbols_path.read_text(encoding="utf-8"))
            for sym in symbols:
                name = sym.get("name", "")
                kind = sym.get("kind", "")
                file_ = sym.get("file", "")
                sig = sym.get("signature") or ""
                line = f"[Symbol: {name}] kind={kind} file={file_}"
                if sig:
                    line += f" signature={sig}"
                symbol_lines.append(line)
        except (json.JSONDecodeError, KeyError):
            pass

    # ── 4. Assemble context within token budget ───────────────────────
    system_prompt = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

    context_parts: list[str] = ["# Knowledge Context\n"]

    # Add wiki pages first (most useful for prose questions)
    for page in page_texts:
        if sum(len(p) for p in context_parts) + len(page) > _CONTEXT_CHAR_BUDGET:
            context_parts.append("\n*[Additional wiki pages omitted — token budget reached]*\n")
            break
        context_parts.append(page)

    # Add symbol index summary
    if symbol_lines:
        sym_section = "\n## Symbol Index\n\n" + "\n".join(symbol_lines)
        remaining = _CONTEXT_CHAR_BUDGET - sum(len(p) for p in context_parts)
        if remaining > 500:
            if len(sym_section) > remaining:
                sym_section = sym_section[:remaining] + "\n*[Symbol index truncated]*"
            context_parts.append(sym_section)

    context = "\n\n".join(context_parts)
    full_system = f"{system_prompt}\n\n{context}"

    # ── 5. Call the LLM ───────────────────────────────────────────────
    client = LLMClient(llm_config)
    return client.call(question, system=full_system)
