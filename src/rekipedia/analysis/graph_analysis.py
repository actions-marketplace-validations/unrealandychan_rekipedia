"""Graph analysis utilities for rekipedia."""
from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rekipedia.models.contracts import Relationship


def compute_god_nodes(
    relationships: "list[Relationship]",
    top_n: int = 10,
) -> list[tuple[str, int]]:
    """Compute in+out degree for each symbol name and return top_n sorted by degree.

    Args:
        relationships: list of Relationship model objects.
        top_n: how many top symbols to return.

    Returns:
        List of (symbol_name, degree) tuples sorted descending by degree.
    """
    degree: dict[str, int] = defaultdict(int)
    for rel in relationships:
        from_name = rel.from_ if hasattr(rel, "from_") else rel.get("from_", "")
        to_name = rel.to if hasattr(rel, "to") else rel.get("to", "")
        if from_name:
            degree[from_name] += 1
        if to_name:
            degree[to_name] += 1

    sorted_nodes = sorted(degree.items(), key=lambda x: x[1], reverse=True)
    return sorted_nodes[:top_n]


def _build_knowledge_gaps(combined: "AnalysisResult") -> list[dict]:
    """Detect symbols with high call counts but no test coverage.

    Args:
        combined: AnalysisResult with symbols and relationships.

    Returns:
        List of dicts with knowledge gap info, sorted by call_count desc, capped at 20.
    """
    from rekipedia.models.contracts import AnalysisResult  # noqa: F401 (type check)

    relationships = combined.relationships if hasattr(combined, "relationships") else []

    # Step 1: Build call-count dict (in-degree for "calls" relationships)
    call_count: dict[str, int] = defaultdict(int)
    for rel in relationships:
        kind = rel.kind if hasattr(rel, "kind") else rel.get("kind", "")
        if str(kind) == "calls":
            to_name = rel.to if hasattr(rel, "to") else rel.get("to", "")
            if to_name:
                call_count[to_name] += 1

    # Step 2: Build test-coverage set
    test_covered: set[str] = set()
    for rel in relationships:
        kind = rel.kind if hasattr(rel, "kind") else rel.get("kind", "")
        if str(kind) != "calls":
            continue
        from_name = rel.from_ if hasattr(rel, "from_") else rel.get("from_", "")
        from_file = rel.file if hasattr(rel, "file") else rel.get("file", "") or ""
        if from_name.startswith("test_") or "/test" in (from_file or ""):
            to_name = rel.to if hasattr(rel, "to") else rel.get("to", "")
            if to_name:
                test_covered.add(to_name)

    # Step 3: Build symbol lookup by name
    symbols = combined.symbols if hasattr(combined, "symbols") else []
    symbol_map: dict[str, object] = {}
    for sym in symbols:
        name = sym.name if hasattr(sym, "name") else sym.get("name", "")
        symbol_map[name] = sym

    # Step 4: Find knowledge gaps
    gaps = []
    valid_kinds = {"function", "method", "class"}
    for name, count in call_count.items():
        if count < 3:
            continue
        if name in test_covered:
            continue
        sym = symbol_map.get(name)
        if sym is None:
            continue
        sym_kind = str(sym.kind if hasattr(sym, "kind") else sym.get("kind", ""))
        if sym_kind not in valid_kinds:
            continue
        sym_file = sym.file if hasattr(sym, "file") else sym.get("file", "")
        gaps.append({
            "name": name,
            "file": sym_file,
            "kind": sym_kind,
            "call_count": count,
            "reason": f"Called {count} times but has no test coverage",
        })

    gaps.sort(key=lambda x: x["call_count"], reverse=True)
    return gaps[:20]
