"""Build Mermaid diagrams from relationship data."""
from __future__ import annotations

import re


class DiagramBuilder:
    """Generate Mermaid diagrams from relationship rows."""

    def build(self, relationships: list) -> dict[str, tuple[str, str]]:
        """Return {name: (diagram_type, mermaid_content)}."""
        results: dict[str, tuple[str, str]] = {}

        if not relationships:
            return results

        # Normalise rows (could be dicts or sqlite3.Row)
        rows = [_to_dict(r) for r in relationships]

        results["module-graph"] = ("flowchart", _build_module_graph(rows))
        results["class-hierarchy"] = ("classDiagram", _build_class_hierarchy(rows))

        return results


# ── diagram builders ─────────────────────────────────────────────────

def _build_module_graph(rows: list[dict]) -> str:
    """flowchart TD showing import relationships between files."""
    edges: set[tuple[str, str]] = set()

    for r in rows:
        frm = r.get("from_") or r.get("from") or ""
        to = r.get("to") or ""
        kind = r.get("kind") or ""

        if kind == "import" and frm and to:
            # Only internal files (no external packages)
            if "/" in to or to.startswith("."):
                edges.add((_sanitise(frm), _sanitise(to)))

    if not edges:
        return "flowchart TD\n  A[No internal imports detected]"

    # Limit to 30 most important edges
    edge_list = list(edges)[:30]

    lines = ["flowchart TD"]
    for frm, to in edge_list:
        lines.append(f"  {frm} --> {to}")
    return "\n".join(lines)


def _build_class_hierarchy(rows: list[dict]) -> str:
    """classDiagram showing inheritance relationships."""
    inheritances: list[tuple[str, str]] = []

    for r in rows:
        if r.get("kind") == "inherits":
            frm = r.get("from_") or r.get("from") or ""
            to = r.get("to") or ""
            if frm and to:
                inheritances.append((_sanitise_class(frm), _sanitise_class(to)))

    if not inheritances:
        return "classDiagram\n  note \"No inheritance relationships detected\""

    lines = ["classDiagram"]
    for child, parent in inheritances[:20]:
        lines.append(f"  {parent} <|-- {child}")
    return "\n".join(lines)


# ── helpers ──────────────────────────────────────────────────────────

def _to_dict(row) -> dict:
    if isinstance(row, dict):
        return row
    try:
        return dict(row)
    except Exception:  # noqa: BLE001
        return {}


def _sanitise(name: str) -> str:
    """Convert a file path to a valid Mermaid node id."""
    # Replace non-alphanumeric characters
    s = re.sub(r"[^A-Za-z0-9_]", "_", name)
    # Ensure doesn't start with digit
    if s and s[0].isdigit():
        s = "_" + s
    return s or "unknown"


def _sanitise_class(name: str) -> str:
    """Strip fully-qualified prefix for class names."""
    return re.sub(r"[^A-Za-z0-9_]", "_", name.split(".")[-1]) or "Unknown"
