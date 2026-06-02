"""Generate REFACTOR.md and refactor_report.json from analysis data.

This module detects refactoring opportunities from an ``AnalysisResult`` and
produces two output artefacts:

* ``REFACTOR.md``  — human/agent-readable Markdown guide
* ``refactor_report.json`` — machine-readable JSON report
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from rekipedia.models.contracts import AnalysisResult, RefactorIssue, Symbol

# ── Severity → presentation mapping ─────────────────────────────────────────

_SEVERITY_EMOJI: dict[str, str] = {
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢",
}

_SECTION_TITLE: dict[str, str] = {
    "high": "High Priority",
    "medium": "Medium Priority",
    "low": "Quick Wins (Dead Code)",
}

# ── Detection thresholds ─────────────────────────────────────────────────────

# A class is considered a "god class" when its combined degree reaches this value.
_GOD_CLASS_DEGREE_THRESHOLD = 10

# Test-related name prefixes/substrings — used to exclude test helpers from
# dead-code detection.
_TEST_PREFIXES = ("test_", "Test", "spec_", "Spec")
_TEST_PATH_SUBSTRINGS = ("/test", "\\test", "_test", "test_", "spec_", "_spec")


def _rekipedia_version() -> str:
    """Return the installed rekipedia package version string."""
    try:
        from importlib.metadata import version as _pkg_version

        return _pkg_version("rekipedia")
    except Exception:
        return "unknown"


def detect_issues(combined: AnalysisResult) -> list[RefactorIssue]:
    """Detect refactoring issues from an ``AnalysisResult``.

    Detects:
    * **god_class** (high severity) — classes/interfaces whose combined
      fan-in + fan-out degree exceeds ``_GOD_CLASS_DEGREE_THRESHOLD``.
    * **dead_code** (low severity) — functions/methods with zero callers that
      are not entry-points, test helpers, or dunder methods.

    Args:
        combined: ``AnalysisResult`` produced by the scan pipeline.

    Returns:
        Sorted list of issue dicts, each containing:
        ``kind``, ``symbol``, ``file``, ``severity``, ``metrics``,
        ``suggestion``, and ``callers``.
    """
    issues: list[RefactorIssue] = []

    # ── Build fan-in / fan-out maps ───────────────────────────────────────────
    fan_in: dict[str, int] = defaultdict(int)   # incoming call edges per symbol
    fan_out: dict[str, int] = defaultdict(int)  # outgoing call edges per symbol
    callers_map: dict[str, list[str]] = defaultdict(list)

    for rel in combined.relationships:
        if rel.from_:
            fan_out[rel.from_] += 1
        if rel.to:
            fan_in[rel.to] += 1
        if str(rel.kind) in ("call", "calls") and rel.from_ and rel.to:
            callers_map[rel.to].append(rel.from_)

    # ── Build symbol lookup ───────────────────────────────────────────────────
    sym_lookup: dict[str, Symbol] = {sym.name: sym for sym in combined.symbols}
    entry_points: set[str] = set(combined.entry_points)

    # ── 1. God Class detection ────────────────────────────────────────────────
    for name, sym in sym_lookup.items():
        kind_str = str(sym.kind)
        if kind_str not in ("class", "interface"):
            continue

        sym_fan_in = fan_in[name]
        sym_fan_out = fan_out[name]
        degree = sym_fan_in + sym_fan_out

        if degree < _GOD_CLASS_DEGREE_THRESHOLD:
            continue

        line_start = sym.line_start or 0
        line_end = sym.line_end or 0
        lines = max(0, line_end - line_start)

        unique_callers = list(dict.fromkeys(callers_map.get(name, [])))
        issues.append(RefactorIssue(
            kind="god_class",
            symbol=name,
            file=sym.file,
            severity="high",
            metrics={"lines": lines, "fan_in": sym_fan_in, "fan_out": sym_fan_out},
            suggestion=f"Split `{name}` into smaller, single-responsibility classes",
            callers=unique_callers[:20],
        ))

    # ── 2. Dead Code detection ────────────────────────────────────────────────
    for name, sym in sym_lookup.items():
        kind_str = str(sym.kind)
        if kind_str not in ("function", "method"):
            continue
        if name in entry_points:
            continue
        # Exclude test helpers and dunder methods
        if any(name.startswith(p) for p in _TEST_PREFIXES):
            continue
        if name.startswith("__") and name.endswith("__"):
            continue
        # Also skip symbols defined in test files
        if any(s in sym.file for s in _TEST_PATH_SUBSTRINGS):
            continue

        if callers_map.get(name):
            continue

        issues.append(RefactorIssue(
            kind="dead_code",
            symbol=name,
            file=sym.file,
            severity="low",
            metrics={"fan_in": 0, "fan_out": fan_out[name]},
            suggestion=f"Remove `{name}` — 0 callers detected",
            callers=[],
        ))

    # ── Sort: high → medium → low, then alphabetically ───────────────────────
    _order = {"high": 0, "medium": 1, "low": 2}
    issues.sort(key=lambda x: (_order.get(x.severity, 99), x.symbol))

    return issues


def _build_markdown(issues: list[RefactorIssue], file_count: int) -> str:
    """Render REFACTOR.md content from the detected issues list.

    Args:
        issues: Sorted list of issue dicts from ``detect_issues``.
        file_count: Number of files seen in the scan (used in the header).

    Returns:
        Full Markdown string ready to be written to disk.
    """
    ver = _rekipedia_version()
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    n_issues = len(issues)

    lines: list[str] = [
        "# Refactoring Guide",
        f"> Generated by rekipedia v{ver} — {timestamp}",
        f"> {n_issues} issue{'s' if n_issues != 1 else ''} found across "
        f"{file_count} file{'s' if file_count != 1 else ''}",
        "",
    ]

    by_severity: dict[str, list[RefactorIssue]] = {"high": [], "medium": [], "low": []}
    for issue in issues:
        sev = issue.severity or "low"
        by_severity.setdefault(sev, []).append(issue)

    for sev in ("high", "medium", "low"):
        sev_issues = by_severity.get(sev, [])
        if not sev_issues:
            continue

        emoji = _SEVERITY_EMOJI[sev]
        title = _SECTION_TITLE[sev]
        lines.append(f"## {emoji} {title}")
        lines.append("")

        if sev == "low":
            # Dead code — compact bulleted list
            for issue in sev_issues:
                sym = issue.symbol
                file_ = issue.file or ""
                note = issue.suggestion.replace(f"Remove `{sym}` — ", "")
                prefix = f"`{file_}:`" if file_ else ""
                lines.append(f"- {prefix}`{sym}()` — {note}")
            lines.append("")
        else:
            for i, issue in enumerate(sev_issues, 1):
                sym = issue.symbol
                kind = issue.kind or ""
                file_ = issue.file or ""
                metrics = issue.metrics or {}
                suggestion = issue.suggestion or ""
                fan_in = metrics.get("fan_in", 0)
                fan_out = metrics.get("fan_out", 0)
                lines_count = metrics.get("lines", 0)

                kind_label = kind.replace("_", " ").title()
                lines.append(f"### {i}. Split `{sym}` ({kind_label})")

                problem_parts: list[str] = []
                if lines_count:
                    problem_parts.append(f"{lines_count} lines")
                if fan_in or fan_out:
                    problem_parts.append(f"fan_in={fan_in}, fan_out={fan_out}")
                problem_str = ", ".join(problem_parts) if problem_parts else "high coupling"

                lines.append(f"- **Problem**: {problem_str}")
                lines.append(f"- **Suggestion**: {suggestion}")
                lines.append(f"- **Callers affected**: {fan_in}")
                if file_:
                    lines.append(f"- **File**: `{file_}`")
                lines.append("")

    return "\n".join(lines) + "\n"


def write_refactor_outputs(
    combined: AnalysisResult,
    output_dir: Path,
    *,
    stdout: bool = False,
) -> tuple[Path, Path]:
    """Write ``REFACTOR.md`` and ``refactor_report.json`` to *output_dir*.

    Args:
        combined: ``AnalysisResult`` from the scan pipeline.
        output_dir: Directory to write output artefacts into.
        stdout: When ``True``, also print ``REFACTOR.md`` content to
            ``sys.stdout`` (useful for piping to Claude Code or other tools).

    Returns:
        Tuple of ``(refactor_md_path, refactor_json_path)``.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    file_count = len(combined.files_seen)
    issues = detect_issues(combined)

    # ── Markdown ──────────────────────────────────────────────────────────────
    md_content = _build_markdown(issues, file_count)
    md_path = output_dir / "REFACTOR.md"
    md_path.write_text(md_content, encoding="utf-8")

    if stdout:
        sys.stdout.write(md_content)
        sys.stdout.flush()

    # ── JSON ──────────────────────────────────────────────────────────────────
    ver = _rekipedia_version()
    summary: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for issue in issues:
        sev = issue.severity or "low"
        summary[sev] = summary.get(sev, 0) + 1

    report: dict = {
        "generated_at": datetime.now(UTC).isoformat(),
        "rekipedia_version": ver,
        "summary": summary,
        "issues": [i.to_dict() for i in issues],
    }
    json_path = output_dir / "refactor_report.json"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return md_path, json_path
