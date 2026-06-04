"""Grounded Q&A pipeline for `rekipedia ask`.

Flow:
    1. Locate the latest successful scan run for this repo.
    2. Load wiki pages from disk (wiki/*.md).
    3. Load symbol index from exports/symbols.json (if present).
    4. RAG retrieval — FAISS top-K source chunks (if index exists).
    5. Assemble a context string, truncated to a token budget.
    6. Call the LLM with a grounding system prompt.
    7. Return the answer text.
"""
from __future__ import annotations

import json
import re as _re
from pathlib import Path
from typing import Iterator

from rekipedia.llm.client import LLMClient
from rekipedia.models.contracts import LLMConfig
from rekipedia.storage.sqlite_store import SqliteStore

_SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "ask_system.md"

# Approximate character budget for context (≈ 24 K tokens at ~4 chars/token).
# Keeps us safely within the context window of most models.
_CONTEXT_CHAR_BUDGET = 96_000

# RAG: number of code chunks to retrieve per question
_RAG_TOP_K = 8


# ---------------------------------------------------------------------------
# Context assembly (shared by run_ask + stream_ask)
# ---------------------------------------------------------------------------

def _verify_scan(output_dir: Path, repo_root: Path) -> str:
    """Return the latest successful run_id, or raise RuntimeError."""
    db_path = output_dir / "store.db"
    if not db_path.exists():
        raise RuntimeError(
            f"No knowledge store found at {db_path}.\n"
            "Run `rekipedia scan .` first."
        )
    with SqliteStore(db_path) as store:
        run_id = store.get_latest_run_id(str(repo_root))
    if run_id is None:
        raise RuntimeError(
            "No successful scan found for this repository.\n"
            "Run `rekipedia scan .` first."
        )
    return run_id


def _load_wiki_pages(output_dir: Path) -> list[str]:
    wiki_dir = output_dir / "wiki"
    pages: list[str] = []
    if wiki_dir.exists():
        for md_file in sorted(wiki_dir.glob("*.md")):
            slug = md_file.stem
            content = md_file.read_text(encoding="utf-8")
            pages.append(f"## [{slug}.md]\n\n{content}")
    return pages


def _load_symbol_lines(output_dir: Path) -> list[str]:
    symbols_path = output_dir / "exports" / "symbols.json"
    lines: list[str] = []
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
                lines.append(line)
        except (json.JSONDecodeError, KeyError):
            pass
    return lines


# Maximum lines to extract per symbol body (avoid flooding context with huge classes)
_SYMBOL_BODY_MAX_LINES = 60


def _extract_symbol_bodies(
    question: str,
    output_dir: Path,
    repo_root: Path,
    top_n: int = 6,
) -> str:
    """Extract actual source code bodies for the top-N symbols most relevant to *question*.

    Returns a formatted Markdown section, or empty string if nothing can be read.
    Only used when RAG index is NOT available (RAG already provides raw source chunks).
    """
    symbols_path = output_dir / "exports" / "symbols.json"
    if not symbols_path.exists():
        return ""

    try:
        symbols = json.loads(symbols_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ""

    if not isinstance(symbols, list):
        return ""

    # Only extract bodies for functions/methods/classes — skip variables/constants
    code_syms = [
        s for s in symbols
        if isinstance(s, dict)
        and s.get("kind") in ("function", "method", "class")
        and s.get("file")
        and s.get("line_start")
    ]
    if not code_syms:
        return ""

    # Rank symbols by keyword overlap with question
    keywords = set(_extract_keywords(question))
    def _sym_score(s: dict) -> float:
        name_words = set(_re.findall(r'[a-z][a-z0-9_]*', s.get("name", "").lower()))
        sig_words = set(_re.findall(r'[a-z][a-z0-9_]*', (s.get("signature") or "").lower()))
        return len(keywords & (name_words | sig_words))

    ranked = sorted(code_syms, key=_sym_score, reverse=True)
    top_syms = [s for s in ranked if _sym_score(s) > 0][:top_n]
    if not top_syms:
        # Fallback: just take the first N symbols if no keyword match
        top_syms = code_syms[:top_n]

    sections: list[str] = []
    for sym in top_syms:
        file_path = Path(sym["file"])
        if not file_path.is_absolute():
            file_path = repo_root / sym["file"]
        if not file_path.exists():
            continue

        try:
            all_lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue

        line_start = max(0, int(sym["line_start"]) - 1)
        line_end_hint = sym.get("line_end")
        if line_end_hint:
            line_end = min(int(line_end_hint), line_start + _SYMBOL_BODY_MAX_LINES)
        else:
            line_end = min(len(all_lines), line_start + _SYMBOL_BODY_MAX_LINES)

        body_lines = all_lines[line_start:line_end]
        if not body_lines:
            continue

        body = "\n".join(body_lines)
        ext = sym["file"].rsplit(".", 1)[-1] if "." in sym["file"] else ""
        ref = f"{sym['file']}:{sym['line_start']}"
        sections.append(
            f"### `{sym['name']}` ({sym['kind']}) — `{ref}`\n\n"
            f"```{ext}\n{body}\n```\n"
        )

    if not sections:
        return ""
    return "## Symbol Source Code\n\n" + "\n".join(sections)


def _rag_chunks(
    question: str,
    output_dir: Path,
    llm_config: LLMConfig,
    top_k: int = _RAG_TOP_K,
) -> list[dict]:
    """Return top-k RAG chunks, or [] if index not available."""
    try:
        from rekipedia.rag.embedder import EmbedPipeline  # noqa: PLC0415

        pipe = EmbedPipeline(output_dir, llm_config)
        if not pipe.is_built():
            return []
        return pipe.search(question, top_k=top_k)
    except Exception:
        return []


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from a query (simple stopword filter)."""
    STOPWORDS = {"the","a","an","is","are","was","were","be","been","being",
                 "have","has","had","do","does","did","will","would","could",
                 "should","may","might","shall","can","need","dare","ought",
                 "used","how","what","where","when","why","who","which","that",
                 "this","these","those","it","its","in","on","at","to","for",
                 "of","with","by","from","up","about","into","through","during"}
    tokens = _re.findall(r'[a-z][a-z0-9_]*', text.lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]


def _score_page(page_text: str, keywords: list[str]) -> float:
    """Score a wiki page against query keywords using TF + importance boost."""
    import re
    # Extract importance from frontmatter
    importance_match = re.search(r'importance:\s*(\d+)', page_text)
    importance = int(importance_match.group(1)) / 100.0 if importance_match else 0.5

    # Extract keywords from frontmatter
    kw_match = re.search(r'keywords:\s*\[([^\]]*)\]', page_text)
    page_keywords = []
    if kw_match:
        page_keywords = [k.strip().strip('"\'') for k in kw_match.group(1).split(',')]

    text_lower = page_text.lower()
    tf_score = sum(text_lower.count(kw) for kw in keywords)
    kw_bonus = sum(2 for kw in keywords if any(kw in pk.lower() for pk in page_keywords))

    length = max(len(page_text), 1)
    return (tf_score + kw_bonus) / length * 1000 + importance * 0.1


def _rank_pages_by_query(pages: list[str], question: str) -> list[str]:
    """Rank wiki pages by relevance to the query."""
    if not pages:
        return pages
    keywords = _extract_keywords(question)
    if not keywords:
        return pages
    scored = [(page, _score_page(page, keywords)) for page in pages]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [p for p, _ in scored]


def _rewrite_query(
    question: str,
    output_dir: Path,
    llm_config: LLMConfig,
) -> str:
    """Silently rewrite query to match codebase vocabulary.

    Returns rewritten query or original if rewrite fails/disabled.
    """
    import os
    if os.environ.get("REKIPEDIA_QUERY_REWRITE", "1") == "0":
        return question

    # Gather vocabulary hints (symbol names + page titles) — lightweight
    vocab_hints: list[str] = []

    symbols_path = output_dir / "exports" / "symbols.json"
    if symbols_path.exists():
        try:
            symbols = json.loads(symbols_path.read_text(encoding="utf-8"))
            # Only include function/class/method names (not variables)
            vocab_hints.extend(
                s.get("name", "") for s in symbols[:200]
                if s.get("kind") in ("function", "class", "method", "interface")
                and s.get("name")
            )
        except Exception:
            pass

    wiki_dir = output_dir / "wiki"
    if wiki_dir.exists():
        for md_file in sorted(wiki_dir.glob("*.md"))[:20]:
            vocab_hints.append(md_file.stem)

    if not vocab_hints or len(vocab_hints) < 15:
        return question

    vocab_sample = ", ".join(vocab_hints[:80])
    rewrite_prompt = (
        "You are a code search assistant. Given a codebase vocabulary and a user question, "
        "rewrite the question to use exact symbol names or terms from the vocabulary. "
        "Return ONLY the rewritten question, one line, no explanation.\n\n"
        f"Vocabulary: {vocab_sample}\n\n"
        f"Original question: {question}\n"
        "Rewritten question:"
    )

    try:
        client = LLMClient(llm_config)
        rewritten = client.call(rewrite_prompt, system="You are a concise code search query rewriter.").strip()
        # Sanity check — don't use if it's too long or empty
        if rewritten and len(rewritten) < len(question) * 3:
            return rewritten
    except Exception:
        pass

    return question


def _load_pinned_context(pinned: list[str], repo_root: Path) -> str:
    """Load and format pinned files/symbols into a context string.

    Args:
        pinned: List of "file" or "file:symbol" strings.
        repo_root: Repository root used to resolve relative paths.

    Returns:
        Formatted Markdown section, or empty string if nothing to pin.
    """
    _TOKEN_BUDGET_CHARS = 16_000
    sections: list[str] = []

    for entry in pinned:
        if ":" in entry:
            file_part, symbol = entry.rsplit(":", 1)
        else:
            file_part, symbol = entry, None

        file_path = Path(file_part)
        if not file_path.is_absolute():
            file_path = repo_root / file_part

        if not file_path.exists():
            sections.append(f"### `{entry}`\n\n*[File not found — skipped]*\n")
            continue

        content = file_path.read_text(encoding="utf-8", errors="replace")

        if symbol:
            # Extract the named function or class using regex
            pattern = _re.compile(
                rf'^(def |class ){_re.escape(symbol)}[\s(:]',
                _re.MULTILINE,
            )
            m = pattern.search(content)
            if m:
                start = m.start()
                # Find end: next top-level def/class or EOF
                end_pattern = _re.compile(r'^(?:def |class )\S', _re.MULTILINE)
                end_m = end_pattern.search(content, start + 1)
                content = content[start:end_m.start() if end_m else len(content)].rstrip()
            else:
                content = f"# Symbol '{symbol}' not found in file\n{content}"

        if len(content) > _TOKEN_BUDGET_CHARS:
            content = content[:_TOKEN_BUDGET_CHARS] + "\n\n*[Content truncated — token budget reached]*"

        label = entry
        lang = file_part.rsplit(".", 1)[-1] if "." in file_part else ""
        sections.append(f"### `{label}`\n\n```{lang}\n{content}\n```\n")

    if not sections:
        return ""
    return "## Pinned Context (--context)\n\n" + "\n".join(sections)


def _build_full_system(
    question: str,
    output_dir: Path,
    llm_config: LLMConfig,
    repo_root: Path | None = None,
    pinned_context: str = "",
) -> str:
    """Assemble the system prompt + all context sources."""
    system_prompt = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

    # Rewrite query to match codebase vocabulary (for retrieval only)
    retrieval_query = _rewrite_query(question, output_dir, llm_config)

    page_texts = _load_wiki_pages(output_dir)
    symbol_lines = _load_symbol_lines(output_dir)
    rag_results = _rag_chunks(retrieval_query, output_dir, llm_config)

    # Context assembly priority (most important first so it appears earliest in prompt):
    #   1. RAG chunks          — most semantically relevant retrieved source code
    #   2. Symbol source code  — actual code bodies for top-N relevant symbols (no RAG fallback)
    #   3. Tech lead notes     — curated team context (if available)
    #   4. Ranked wiki pages   — broad curated prose, ranked by query relevance
    #   5. Symbol index        — fallback structural reference (often large)
    # This order mirrors the Go runtime (go/internal/orchestrator/run_ask.go).
    context_parts: list[str] = ["# Knowledge Context\n"]
    used_chars = sum(len(p) for p in context_parts)

    # ── 0. Pinned context (--context flag, highest priority) ──────────
    if pinned_context:
        context_parts.insert(1, pinned_context)
        used_chars += len(pinned_context)

    # ── 1. RAG: raw source code chunks (highest priority) ─────────────
    if rag_results:
        rag_header = "\n## Relevant Source Code (RAG)\n"
        if used_chars + len(rag_header) < _CONTEXT_CHAR_BUDGET:
            context_parts.append(rag_header)
            used_chars += len(rag_header)
            for chunk in rag_results:
                file_ = chunk.get("file", "")
                ext = chunk.get("ext", "")
                lang = ext.lstrip(".") if ext else ""
                score = chunk.get("score", 0.0)
                text = chunk.get("text", "")
                snippet = (
                    f"\n### `{file_}` (relevance={score:.2f})\n"
                    f"```{lang}\n{text}\n```\n"
                )
                if used_chars + len(snippet) > _CONTEXT_CHAR_BUDGET:
                    break
                context_parts.append(snippet)
                used_chars += len(snippet)

    # ── 1b. Symbol source bodies (when no RAG index — keyword-ranked) ──
    if not rag_results and repo_root is not None:
        sym_bodies = _extract_symbol_bodies(retrieval_query, output_dir, repo_root)
        if sym_bodies and used_chars + len(sym_bodies) < _CONTEXT_CHAR_BUDGET:
            context_parts.append(sym_bodies)
            used_chars += len(sym_bodies)

    # ── 2. Tech Lead Notes (if available) ─────────────────────────────
    try:
        db_path = output_dir / "store.db"
        if db_path.exists():
            with SqliteStore(db_path) as _note_store:
                all_notes = _note_store.list_notes()
            if all_notes:
                # BM25-style keyword filter: rank by word overlap with question
                _kws = set(_extract_keywords(question))
                def _note_score(n: dict) -> float:
                    if not _kws:
                        return 1.0
                    words = set(_re.findall(r'[a-z][a-z0-9_]*', (n["content"] + " " + n["tags"]).lower()))
                    return len(_kws & words)
                _max_notes = 5
                scored_notes = sorted(all_notes, key=_note_score, reverse=True)[:_max_notes]
                relevant_notes = [n for n in scored_notes if _note_score(n) > 0 or len(all_notes) <= _max_notes]
                if not relevant_notes:
                    relevant_notes = scored_notes
                notes_section = "## Team Context / Tech Lead Notes\n\n"
                for n in relevant_notes:
                    tag_prefix = f"[{n['tags']}] " if n["tags"] else ""
                    notes_section += f"{tag_prefix}{n['content']}\n\n"
                if used_chars + len(notes_section) < _CONTEXT_CHAR_BUDGET:
                    context_parts.append(notes_section)
                    used_chars += len(notes_section)
    except Exception:
        pass  # notes are optional — never break ask

    # ── 3. Wiki pages (ranked by query relevance) ──────────────────────
    ranked_pages = _rank_pages_by_query(page_texts, retrieval_query)
    for page in ranked_pages:
        if used_chars + len(page) > _CONTEXT_CHAR_BUDGET:
            context_parts.append(
                "\n*[Additional wiki pages omitted — token budget reached]*\n"
            )
            break
        context_parts.append(page)
        used_chars += len(page)

    # ── 4. Symbol index (fallback) ─────────────────────────────────────
    if symbol_lines:
        sym_section = "\n## Symbol Index\n\n" + "\n".join(symbol_lines)
        remaining = _CONTEXT_CHAR_BUDGET - used_chars
        if remaining > 500:
            if len(sym_section) > remaining:
                sym_section = sym_section[:remaining] + "\n*[Symbol index truncated]*"
            context_parts.append(sym_section)

    context = "\n\n".join(context_parts)
    return f"{system_prompt}\n\n{context}"


# ---------------------------------------------------------------------------
# Shared setup helper
# ---------------------------------------------------------------------------

def _prepare_ask(
    question: str,
    repo_root: Path,
    output_dir: Path,
    llm_config: LLMConfig | None,
    history: list[dict] | None,  # noqa: ARG001 — reserved for future use
    pinned_context: str = "",
) -> tuple[LLMClient, str]:
    """Validate scan, build system prompt, and init LLM client.

    Returns:
        (client, full_system_prompt) ready to pass to ``client.call`` /
        ``client.stream``.
    """
    llm_config = llm_config or LLMConfig()
    _verify_scan(output_dir, repo_root)
    full_system = _build_full_system(question, output_dir, llm_config, repo_root=repo_root, pinned_context=pinned_context)
    client = LLMClient(llm_config)
    return client, full_system


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_ask(
    question: str,
    repo_root: Path,
    output_dir: Path,
    llm_config: LLMConfig | None = None,
    history: list[dict] | None = None,
    pinned_context: list[str] | None = None,
) -> str:
    """Answer *question* grounded in the knowledge store.

    Args:
        question: Free-text question from the user.
        repo_root: Absolute path to the repository.
        output_dir: `.rekipedia/` directory containing store.db + wiki/.
        llm_config: LLM settings; defaults to LLMConfig().
        history: Previous conversation turns as [{role, content}, ...].
        pinned_context: List of file[:symbol] strings to pin into context.

    Returns:
        The assistant's answer as a Markdown string.

    Raises:
        RuntimeError: If no successful scan exists for the repo.
    """
    import os as _os
    if _os.environ.get("REKIPEDIA_AGENT_ASK", "0") == "1":
        from rekipedia.orchestrator.agent_ask import agent_run_ask  # noqa: PLC0415
        return agent_run_ask(question, repo_root, output_dir, llm_config, history)
    pinned_str = _load_pinned_context(pinned_context or [], repo_root)
    client, full_system = _prepare_ask(question, repo_root, output_dir, llm_config, history, pinned_context=pinned_str)
    return client.call(question, system=full_system, history=history)


def stream_ask(
    question: str,
    repo_root: Path,
    output_dir: Path,
    llm_config: LLMConfig | None = None,
    history: list[dict] | None = None,
    pinned_context: list[str] | None = None,
) -> Iterator[str]:
    """Answer *question* grounded in the knowledge store, streaming tokens.

    Identical to :func:`run_ask` except the final LLM call uses streaming
    and yields text chunks instead of returning a single string.
    """
    pinned_str = _load_pinned_context(pinned_context or [], repo_root)
    client, full_system = _prepare_ask(question, repo_root, output_dir, llm_config, history, pinned_context=pinned_str)
    return client.stream(question, system=full_system, history=history)
