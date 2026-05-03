"""TypeScript/JavaScript extractor using regex (no binary tree-sitter dep)."""
from __future__ import annotations

import re
from pathlib import Path

from rekipedia.extractors.base import BaseExtractor
from rekipedia.models.contracts import AnalysisResult, RationaleNote, Relationship, Symbol

_TS_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}

# Patterns
_RE_IMPORT = re.compile(
    r"""(?:import\s+(?:.*?\s+from\s+)?|require\s*\()\s*['"]([^'"]+)['"]""",
    re.MULTILINE,
)
_RE_EXPORT_FUNC = re.compile(
    r"""(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)""",
    re.MULTILINE,
)
_RE_ARROW_FUNC = re.compile(
    r"""(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>""",
    re.MULTILINE,
)
_RE_CLASS = re.compile(
    r"""(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?""",
    re.MULTILINE,
)
_RE_INTERFACE = re.compile(r"""(?:export\s+)?interface\s+(\w+)""", re.MULTILINE)
_RE_TYPE = re.compile(r"""(?:export\s+)?type\s+(\w+)\s*=""", re.MULTILINE)
_RE_JSDOC = re.compile(r"""/\*\*(.*?)\*/""", re.DOTALL)
_RE_RATIONALE = re.compile(r"//\s*(NOTE|IMPORTANT|HACK|WHY|TODO):\s*(.*)", re.IGNORECASE)


class TypeScriptExtractor(BaseExtractor):
    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in _TS_SUFFIXES

    def extract(self, path: Path, repo_root: Path) -> AnalysisResult:
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return AnalysisResult(shard_id=rel, files_seen=[rel], entry_points=[])

        symbols: list[Symbol] = []
        relationships: list[Relationship] = []
        rationale_notes: list[RationaleNote] = []

        # ── rationale notes ───────────────────────────────────────────
        for lineno, line in enumerate(source.splitlines(), start=1):
            m = _RE_RATIONALE.search(line)
            if m:
                tag = m.group(1).upper()
                rationale_notes.append(
                    RationaleNote(tag=tag, content=m.group(2).strip(), file=rel, line=lineno)  # type: ignore[arg-type]
                )

        # strip comments to avoid false matches, keep line count stable
        clean = re.sub(r"//[^\n]*", "", source)

        # ── imports ──────────────────────────────────────────────────
        for m in _RE_IMPORT.finditer(clean):
            relationships.append(
                Relationship.model_validate(
                    {"from": rel, "to": m.group(1), "kind": "import", "file": rel,
                     "confidence": 1.0, "evidence_tag": "EXTRACTED"}
                )
            )

        # ── functions ────────────────────────────────────────────────
        for m in _RE_EXPORT_FUNC.finditer(clean):
            symbols.append(
                Symbol(
                    name=m.group(1),
                    kind="function",
                    file=rel,
                    line_start=_line_of(source, m.start()),
                    signature=f"{m.group(1)}({m.group(2).strip()})",
                )
            )
        for m in _RE_ARROW_FUNC.finditer(clean):
            symbols.append(
                Symbol(
                    name=m.group(1),
                    kind="function",
                    file=rel,
                    line_start=_line_of(source, m.start()),
                    signature=f"{m.group(1)}({m.group(2).strip()})",
                )
            )

        # ── classes ──────────────────────────────────────────────────
        for m in _RE_CLASS.finditer(clean):
            symbols.append(
                Symbol(name=m.group(1), kind="class", file=rel, line_start=_line_of(source, m.start()))
            )
            if m.group(2):
                relationships.append(
                    Relationship.model_validate(
                        {"from": m.group(1), "to": m.group(2), "kind": "inherits", "file": rel,
                         "confidence": 1.0, "evidence_tag": "EXTRACTED"}
                    )
                )

        # ── interfaces / types ───────────────────────────────────────
        for m in _RE_INTERFACE.finditer(clean):
            symbols.append(Symbol(name=m.group(1), kind="interface", file=rel, line_start=_line_of(source, m.start())))
        for m in _RE_TYPE.finditer(clean):
            symbols.append(Symbol(name=m.group(1), kind="type", file=rel, line_start=_line_of(source, m.start())))

        entry_points: list[str] = []
        if path.name in {"index.ts", "index.js", "main.ts", "main.js", "server.ts", "server.js", "app.ts", "app.js"}:
            entry_points = [rel]

        return AnalysisResult(
            shard_id=rel,
            files_seen=[rel],
            entry_points=entry_points,
            symbols=symbols,
            relationships=relationships,
            rationale_notes=rationale_notes,
        )


def _line_of(source: str, offset: int) -> int:
    return source[:offset].count("\n") + 1
