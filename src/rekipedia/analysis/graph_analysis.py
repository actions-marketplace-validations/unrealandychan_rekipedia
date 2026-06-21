"""Graph analysis utilities for rekipedia."""
from __future__ import annotations

import os
from collections import defaultdict
from typing import TYPE_CHECKING

# Minimum call count for a symbol to be flagged as a knowledge gap.
# Override with REKIPEDIA_GAP_MIN_CALLS env var.
_GAP_MIN_CALLS = int(os.environ.get("REKIPEDIA_GAP_MIN_CALLS", "3"))

if TYPE_CHECKING:
    from rekipedia.models.contracts import AnalysisResult, Relationship


def compute_god_nodes(
    relationships: list[Relationship],
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


def _build_knowledge_gaps(combined: AnalysisResult) -> list[dict]:
    """Detect symbols with high call counts but no test coverage.

    Args:
        combined: AnalysisResult with symbols and relationships.

    Returns:
        List of dicts with knowledge gap info, sorted by call_count desc, capped at 20.
    """
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
        if count < _GAP_MIN_CALLS:
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


def _build_hub_nodes(
    relationships: list,
    symbols: list = None,
    top_n: int = 20,
) -> list[dict]:
    """Find hub nodes using a degree-based approximation of centrality.

    Uses combined in+out degree as a proxy for betweenness centrality
    (avoids networkx dependency for large graphs, O(N) not O(N^3)).

    Returns top_n nodes with highest combined degree, enriched with symbol info.
    """
    from collections import defaultdict
    in_deg: dict[str, int] = defaultdict(int)
    out_deg: dict[str, int] = defaultdict(int)

    for rel in relationships:
        from_name = rel.from_ if hasattr(rel, "from_") else rel.get("from_", "") or rel.get("from", "")
        to_name = rel.to if hasattr(rel, "to") else rel.get("to", "")
        if from_name:
            out_deg[from_name] += 1
        if to_name:
            in_deg[to_name] += 1

    all_nodes = set(in_deg) | set(out_deg)

    # Build symbol lookup
    sym_lookup: dict[str, dict] = {}
    if symbols:
        for s in symbols:
            name = s.name if hasattr(s, "name") else s.get("name", "")
            sym_lookup[name] = {
                "file": s.file if hasattr(s, "file") else s.get("file", ""),
                "kind": s.kind if hasattr(s, "kind") else s.get("kind", ""),
            }

    scored = []
    for node in all_nodes:
        i = in_deg[node]
        o = out_deg[node]
        score = i + o
        # bridge: high in AND high out (not just a leaf)
        is_bridge = i >= 2 and o >= 2
        sym = sym_lookup.get(node, {})
        scored.append({
            "name": node,
            "file": sym.get("file", ""),
            "kind": sym.get("kind", ""),
            "in_degree": i,
            "out_degree": o,
            "score": score,
            "is_bridge": is_bridge,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


def get_hub_nodes(store: SqliteStore, run_id: str, top_n: int = 10) -> list[dict]:
    """Return top N hub nodes (most connected symbols) from the stored graph."""
    relationships = store.get_all_relationships(run_id)
    symbols = store.get_all_symbols(run_id)
    all_scored = _build_hub_nodes(relationships, symbols, top_n=top_n * 3)

    from rekipedia.analysis.git_history import get_file_commit_counts
    commit_counts = get_file_commit_counts(store, run_id)

    for n in all_scored:
        file_path = n.get("file", "")
        commit_count = commit_counts.get(file_path, 0)
        n["commit_count"] = commit_count
        # Factoring commit frequency into the score
        n["score"] = n.get("score", n["in_degree"] + n["out_degree"]) + commit_count
        n["total_degree"] = n["score"]

    all_scored.sort(key=lambda x: x["score"], reverse=True)
    return all_scored[:top_n]


def get_bridge_nodes(store: SqliteStore, run_id: str, top_n: int = 10) -> list[dict]:
    """Return top N bridge nodes (cross-boundary connectors: high in AND high out degree)."""
    relationships = store.get_all_relationships(run_id)
    symbols = store.get_all_symbols(run_id)
    all_scored = _build_hub_nodes(relationships, symbols, top_n=9999)

    from rekipedia.analysis.git_history import get_file_commit_counts
    commit_counts = get_file_commit_counts(store, run_id)

    bridges = [n for n in all_scored if n.get("is_bridge")]
    for b in bridges:
        file_path = b.get("file", "")
        commit_count = commit_counts.get(file_path, 0)
        b["commit_count"] = commit_count
        b["bridge_score"] = b["in_degree"] * b["out_degree"] + commit_count

    bridges.sort(key=lambda x: x["bridge_score"], reverse=True)
    return bridges[:top_n]


def compute_shortest_path(
    from_symbol: str,
    to_symbol: str,
    relationships: list,
) -> dict:
    """BFS shortest path between two symbols in the directed relationship graph.

    Args:
        from_symbol: Source symbol name.
        to_symbol: Target symbol name.
        relationships: List of relationship dicts or Relationship objects.

    Returns:
        Dict with keys:
        - ``path``: list[str] from source to target (inclusive), or None if
          unreachable.  A trivial self-path ``[X]`` is returned when
          ``from_symbol == to_symbol``.
        - ``length``: int hop count (0 for self-path), or None if unreachable.
    """
    from collections import deque

    # Trivial self-path: symbol reaches itself with 0 hops
    if from_symbol == to_symbol:
        return {"path": [from_symbol], "length": 0}

    # Build directed adjacency list
    graph: dict[str, list[str]] = {}
    for rel in relationships:
        if isinstance(rel, dict):
            frm = rel.get("from_", "") or rel.get("from", "")
            to  = rel.get("to", "")
        else:
            frm = rel.from_ or ""
            to  = rel.to or ""
        if frm and to:
            graph.setdefault(frm, []).append(to)

    if from_symbol not in graph:
        return {"path": None, "length": None}

    # BFS — store full paths to reconstruct shortest
    queue: deque[list[str]] = deque([[from_symbol]])
    visited: set[str] = {from_symbol}
    while queue:
        path = queue.popleft()
        current = path[-1]
        for neighbour in graph.get(current, []):
            if neighbour == to_symbol:
                full_path = path + [neighbour]
                return {"path": full_path, "length": len(full_path) - 1}
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append(path + [neighbour])

    return {"path": None, "length": None}
