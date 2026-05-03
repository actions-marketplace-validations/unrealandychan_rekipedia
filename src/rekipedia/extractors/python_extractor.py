"""Python source extractor using stdlib ast."""
from __future__ import annotations

import ast
import re
from pathlib import Path

from rekipedia.extractors.base import BaseExtractor
from rekipedia.models.contracts import AnalysisResult, RationaleNote, Relationship, Symbol

_PY_SUFFIXES = {".py", ".pyw"}

_RATIONALE_RE = re.compile(
    r"#\s*(NOTE|IMPORTANT|HACK|WHY|TODO):\s*(.*)", re.IGNORECASE
)


class PythonExtractor(BaseExtractor):
    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in _PY_SUFFIXES

    def extract(self, path: Path, repo_root: Path) -> AnalysisResult:
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            return AnalysisResult(
                shard_id=rel,
                files_seen=[rel],
                entry_points=[],
                risks=[f"SyntaxError in {rel}"],
            )

        symbols: list[Symbol] = []
        relationships: list[Relationship] = []
        rationale_notes: list[RationaleNote] = []

        # ── rationale notes from source lines ────────────────────────
        for lineno, line in enumerate(source.splitlines(), start=1):
            m = _RATIONALE_RE.search(line)
            if m:
                tag = m.group(1).upper()
                rationale_notes.append(
                    RationaleNote(tag=tag, content=m.group(2).strip(), file=rel, line=lineno)  # type: ignore[arg-type]
                )

        # ── imports ──────────────────────────────────────────────────
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    relationships.append(
                        Relationship.model_validate(
                            {"from": rel, "to": alias.name, "kind": "import", "file": rel,
                             "confidence": 1.0, "evidence_tag": "EXTRACTED"}
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                relationships.append(
                    Relationship.model_validate(
                        {"from": rel, "to": module, "kind": "import", "file": rel,
                         "confidence": 1.0, "evidence_tag": "EXTRACTED"}
                    )
                )

        # ── top-level definitions ────────────────────────────────────
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append(
                    Symbol(
                        name=node.name,
                        kind="function",
                        file=rel,
                        line_start=node.lineno,
                        line_end=node.end_lineno,
                        docstring=ast.get_docstring(node),
                        signature=_func_sig(node),
                    )
                )
            elif isinstance(node, ast.ClassDef):
                symbols.append(
                    Symbol(
                        name=node.name,
                        kind="class",
                        file=rel,
                        line_start=node.lineno,
                        line_end=node.end_lineno,
                        docstring=ast.get_docstring(node),
                    )
                )
                # methods
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        symbols.append(
                            Symbol(
                                name=f"{node.name}.{child.name}",
                                kind="function",
                                file=rel,
                                line_start=child.lineno,
                                line_end=child.end_lineno,
                                docstring=ast.get_docstring(child),
                                signature=_func_sig(child),
                            )
                        )
                # inheritance
                for base in node.bases:
                    base_name = _name_to_str(base)
                    if base_name:
                        relationships.append(
                            Relationship.model_validate(
                                {
                                    "from": node.name,
                                    "to": base_name,
                                    "kind": "inherits",
                                    "file": rel,
                                    "confidence": 1.0,
                                    "evidence_tag": "EXTRACTED",
                                }
                            )
                        )

        entry_points = _detect_entry_points(tree, rel)

        return AnalysisResult(
            shard_id=rel,
            files_seen=[rel],
            entry_points=entry_points,
            symbols=symbols,
            relationships=relationships,
            rationale_notes=rationale_notes,
        )



# ── helpers ──────────────────────────────────────────────────────────

def _func_sig(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = []
    for arg in node.args.args:
        args.append(arg.arg)
    return f"{node.name}({', '.join(args)})"


def _name_to_str(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_name_to_str(node.value)}.{node.attr}"
    return ""


def _detect_entry_points(tree: ast.Module, rel: str) -> list[str]:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "__name__"
        ):
            return [rel]
    return []
