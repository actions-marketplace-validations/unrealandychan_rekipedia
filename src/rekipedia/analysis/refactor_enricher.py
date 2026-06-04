"""LLM enrichment of static-analysis refactoring issues.

For each issue detected by static analysis, uses the LLM to produce a
human-readable explanation and a concrete refactoring suggestion.

Typical usage::

    from rekipedia.analysis.refactor_enricher import RefactorEnricher, detect_issues

    issues = detect_issues(combined)          # pure static analysis
    enricher = RefactorEnricher(llm_caller)   # pass None to skip LLM
    enriched = enricher.enrich(issues, combined)
"""
from __future__ import annotations

import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

from rekipedia.models.contracts import RefactorIssue

if TYPE_CHECKING:
    from collections.abc import Callable

    from rekipedia.llm.client import LLMCaller
    from rekipedia.models.contracts import AnalysisResult

logger = logging.getLogger("rekipedia.refactor_enricher")

# ── Thresholds ───────────────────────────────────────────────────────────────

_GOD_CLASS_DEGREE_THRESHOLD = 10
_LARGE_FILE_SYMBOL_THRESHOLD = 30
_LARGE_FILE_BYTES_THRESHOLD = 500_000   # 500 KB — flag files that are simply too big
_HIGH_COUPLING_OUT_THRESHOLD = 10
_DEAD_CODE_MIN_FILE_SYMBOLS = 3  # ignore tiny files; only flag in larger files
_MAX_ENRICHER_WORKERS = 4

# ── Prompt templates ─────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a senior software architect reviewing code for refactoring opportunities.
Given a code issue detected by static analysis, produce a concise, actionable
refactoring recommendation.

Respond in EXACTLY this format — no extra text, no markdown headers:
Problem: <one sentence describing the concrete issue>
Suggestion: <specific refactoring action — name the new components/functions>
Start here: <file or component — the safest/lowest-coupling place to begin>
Risk: <Low|Medium|High> — <one sentence explaining the primary risk>"""

_ISSUE_PROMPTS: dict[str, str] = {
    "god_class": """\
Symbol: {symbol}
File: {file}
Issue type: God class / hub node
Degree: {degree} ({in_degree} callers, {out_degree} outbound dependencies)
Top callers: {callers}
Relevant notes: {notes}

This symbol has extremely high coupling, suggesting it handles too many responsibilities.
Suggest how to split it into focused, single-responsibility components.""",

    "circular_dep": """\
Cycle members: {symbol}
Files involved: {file}
Issue type: Circular dependency
Cycle length: {cycle_length}
Relevant notes: {notes}

This circular dependency creates tight coupling and makes the code hard to test or deploy.
Suggest how to break the cycle using dependency inversion or an intermediary module.""",

    "dead_code": """\
Symbol: {symbol}
File: {file}
Issue type: Dead code — no callers detected
Total symbols in file: {total_symbols}
Relevant notes: {notes}

This exported symbol appears to be unused by any other module.
Suggest whether to remove it, deprecate it, or repurpose it.""",

    "large_file": """\
File: {file}
Issue type: Large file — too many symbols
Symbol count: {symbol_count}
Top symbols: {symbol}
Relevant notes: {notes}

This file defines too many symbols and likely handles multiple concerns.
Suggest how to split it into focused, cohesive modules.""",

    "high_coupling": """\
Symbol: {symbol}
File: {file}
Issue type: High coupling — too many outbound dependencies
Outbound dependencies: {out_degree}
Top dependencies: {callers}
Relevant notes: {notes}

This symbol imports from / calls too many distinct modules.
Suggest dependency-reduction strategies (facade, adapter, or domain split).""",
}


# ── Static analysis detectors ────────────────────────────────────────────────


def detect_issues(combined: AnalysisResult) -> list[RefactorIssue]:
    """Delegate to the canonical detector in refactor_detector.py.

    Kept here for backward-compatibility with existing imports.
    """
    from rekipedia.analysis.refactor_detector import detect_issues as _detect
    return _detect(combined)


# ── Helpers: cycle detection ─────────────────────────────────────────────────


def _find_cycles(adj: dict[str, set[str]]) -> list[frozenset[str]]:
    """Return small cycles (≤8 nodes) in the directed graph *adj*.

    Uses iterative DFS with a path stack.  Caps results at 20 to avoid
    flooding the output for repositories with many cycles.
    """
    found: list[frozenset[str]] = []
    seen_sets: set[frozenset[str]] = set()

    def _dfs_from(start: str) -> None:
        stack: list[tuple[str, list[str]]] = [(start, [start])]
        while stack:
            node, path = stack.pop()
            for neighbour in adj.get(node, ()):
                if len(found) >= 20:
                    return
                if neighbour == path[0]:
                    # Back-edge to start: cycle found
                    key = frozenset(path)
                    if key not in seen_sets and len(key) >= 2:
                        seen_sets.add(key)
                        found.append(key)
                elif neighbour not in path and len(path) < 8:
                    stack.append((neighbour, path + [neighbour]))

    for node in list(adj):
        if len(found) >= 20:
            break
        _dfs_from(node)

    return found


# ── Helpers: attach callers & notes ─────────────────────────────────────────


def _attach_callers(
    issues: list[RefactorIssue],
    combined: AnalysisResult,
    top_n: int = 5,
) -> None:
    """Populate issue.callers with the top-N callers for each issue symbol."""
    relationships = combined.relationships if hasattr(combined, "relationships") else []

    # callers_of[sym] = list of caller names
    callers_of: dict[str, list[str]] = defaultdict(list)
    for rel in relationships:
        from_name = rel.from_ if hasattr(rel, "from_") else rel.get("from_", "")
        to_name = rel.to if hasattr(rel, "to") else rel.get("to", "")
        kind = str(rel.kind if hasattr(rel, "kind") else rel.get("kind", ""))
        if kind in ("call", "calls") and from_name and to_name:
            callers_of[to_name].append(from_name)

    for issue in issues:
        callers = callers_of.get(issue.symbol, [])
        # de-duplicate while preserving order
        seen_c: set[str] = set()
        unique: list[str] = []
        for c in callers:
            if c not in seen_c:
                seen_c.add(c)
                unique.append(c)
        issue.callers = unique[:top_n]


def _attach_notes(
    issues: list[RefactorIssue],
    notes: list[dict],
) -> None:
    """Attach relevant tech-lead notes to each issue based on file match."""
    # Group notes by file
    notes_by_file: dict[str, list[str]] = defaultdict(list)
    for note in notes:
        f = note.get("file", "")
        content = note.get("content", "")
        if f and content:
            notes_by_file[f].append(f"[{note.get('tag', 'NOTE')}] {content}")

    for issue in issues:
        matched: list[str] = []
        for fpath, note_texts in notes_by_file.items():
            if fpath and issue.file and (fpath in issue.file or issue.file in fpath):
                matched.extend(note_texts)
        issue.notes = matched[:5]


# ── LLM enricher ─────────────────────────────────────────────────────────────


class RefactorEnricher:
    """Enrich static-analysis issues with LLM explanations and suggestions.

    Pass ``caller=None`` (or use ``--no-llm``) to skip LLM calls — static
    analysis output is returned unchanged.

    Example::

        enricher = RefactorEnricher(llm_caller)
        enriched = enricher.enrich_all(combined, notes=tech_lead_notes)
    """

    def __init__(self, caller: LLMCaller | None = None) -> None:
        self._caller = caller

    # ── Public API ───────────────────────────────────────────────────

    def enrich_all(
        self,
        combined: AnalysisResult,
        *,
        notes: list[dict] | None = None,
        progress_cb: Callable[[str], None] | None = None,
    ) -> list[RefactorIssue]:
        """Detect issues from *combined* and enrich them with LLM explanations.

        Args:
            combined: Merged AnalysisResult from all shards.
            notes: Optional list of tech-lead notes (from sqlite_store).
            progress_cb: Optional callback receiving status strings.

        Returns:
            List of RefactorIssues, each with ``problem``, ``suggestion``,
            ``start_here``, and ``risk`` populated (or empty strings if
            ``--no-llm`` / no caller supplied).
        """
        issues = detect_issues(combined)
        _attach_callers(issues, combined)
        if notes:
            _attach_notes(issues, notes)
        return self.enrich(issues, progress_cb=progress_cb)

    def enrich(self, issues: list[RefactorIssue], *, progress_cb: Callable[[str], None] | None = None) -> list[RefactorIssue]:
        """Enrich *issues* with LLM explanations (batch, concurrent).

        If no LLM caller was provided the issues are returned unchanged —
        ``problem`` / ``suggestion`` / ``start_here`` / ``risk`` stay empty.

        Args:
            issues: Issues produced by :func:`detect_issues`.

        Returns:
            The same list, mutated in-place (also returned for convenience).
        """
        if not self._caller or not issues:
            return issues

        _cb = progress_cb or (lambda _: None)
        _done = 0

        with ThreadPoolExecutor(max_workers=_MAX_ENRICHER_WORKERS) as executor:
            futures = {
                executor.submit(self._enrich_one, issue): issue
                for issue in issues
            }
            for future in as_completed(futures):
                issue = futures[future]
                try:
                    future.result()
                except Exception as exc:
                    logger.warning("Enrichment failed for %s/%s: %s", issue.kind, issue.symbol, exc)
                finally:
                    _done += 1
                    _cb(f"Enriched {_done}/{len(issues)} refactor issues")
        return issues

    # ── Internal ─────────────────────────────────────────────────────

    def _enrich_one(self, issue: RefactorIssue) -> None:
        """Call the LLM for a single issue and mutate it in-place."""
        assert self._caller is not None
        prompt = _build_prompt(issue)
        try:
            raw = self._caller.call(prompt, system=_SYSTEM_PROMPT)
        except Exception as exc:
            logger.debug("LLM call failed for %s: %s", issue.symbol, exc)
            raise
        _parse_enrichment(raw, issue)


# ── Prompt / response helpers ─────────────────────────────────────────────────


def _build_prompt(issue: RefactorIssue) -> str:
    """Build the LLM user prompt for *issue* using the per-kind template."""
    template = _ISSUE_PROMPTS.get(issue.kind, _ISSUE_PROMPTS["god_class"])
    callers_str = ", ".join(issue.callers) if issue.callers else "(none detected)"
    notes_str = "; ".join(issue.notes) if issue.notes else "(none)"
    ctx = {
        "symbol": issue.symbol,
        "file": issue.file or "(unknown)",
        "callers": callers_str,
        "notes": notes_str,
        **issue.metrics,
    }
    # Ensure all required keys have a default fallback
    ctx.setdefault("degree", issue.metrics.get("degree", 0))
    ctx.setdefault("in_degree", issue.metrics.get("in_degree", 0))
    ctx.setdefault("out_degree", issue.metrics.get("out_degree", 0))
    ctx.setdefault("cycle_length", issue.metrics.get("cycle_length", 0))
    ctx.setdefault("members", issue.metrics.get("members", []))
    ctx.setdefault("total_symbols", issue.metrics.get("total_symbols", 0))
    ctx.setdefault("symbol_count", issue.metrics.get("symbol_count", 0))
    return template.format(**ctx)


def _parse_enrichment(raw: str, issue: RefactorIssue) -> None:
    """Parse the 4-line LLM response and populate *issue* fields in-place.

    Expected format (each line optional / order-independent)::

        Problem: …
        Suggestion: …
        Start here: …
        Risk: …
    """
    for line in raw.splitlines():
        line = line.strip()
        lower = line.lower()
        if lower.startswith("problem:"):
            issue.problem = line[len("problem:"):].strip()
        elif lower.startswith("suggestion:"):
            issue.suggestion = line[len("suggestion:"):].strip()
        elif lower.startswith("start here:"):
            issue.start_here = line[len("start here:"):].strip()
        elif lower.startswith("risk:"):
            issue.risk = line[len("risk:"):].strip()
