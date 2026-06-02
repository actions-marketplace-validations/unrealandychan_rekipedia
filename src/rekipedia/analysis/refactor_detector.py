"""Graph-based static analysis metrics for refactoring detection.

Analyses the symbol/relationship graph to detect code smells without LLM.
Reuses patterns from graph_analysis.py (hub_bridge, knowledge_gap).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from rekipedia.models.contracts import RefactorIssue


@dataclass
class RefactorConfig:
    """Thresholds for refactor checks, overridable via .rekipedia/config.yml refactor: block."""

    god_node_top_pct: float = 0.05      # top 5% by fan-in + fan-out
    high_fan_in: int = 20               # > N callers
    high_fan_out: int = 15              # > N dependencies
    deep_inheritance_depth: int = 3     # depth > N


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_from(rel: object) -> str:
    return rel.from_ if hasattr(rel, "from_") else rel.get("from_", "") or rel.get("from", "")  # type: ignore[union-attr]


def _get_to(rel: object) -> str:
    return rel.to if hasattr(rel, "to") else rel.get("to", "")  # type: ignore[union-attr]


def _get_kind(rel: object) -> str:
    return str(rel.kind if hasattr(rel, "kind") else rel.get("kind", ""))  # type: ignore[union-attr]


def _sym_name(sym: object) -> str:
    return sym.name if hasattr(sym, "name") else sym.get("name", "")  # type: ignore[union-attr]


def _sym_file(sym: object) -> str:
    return sym.file if hasattr(sym, "file") else sym.get("file", "") or ""  # type: ignore[union-attr]


def _sym_kind(sym: object) -> str:
    return str(sym.kind if hasattr(sym, "kind") else sym.get("kind", ""))  # type: ignore[union-attr]


def _build_sym_lookup(symbols: list) -> dict[str, object]:
    return {_sym_name(s): s for s in (symbols or [])}


def _is_exported(name: str, file: str) -> bool:
    """Return True if the symbol is considered exported/public.

    * Go (.go files): exported = first letter uppercase
    * Python and other languages: public = name does not start with ``_``
    """
    if not name:
        return True
    if file.endswith(".go"):
        return name[0].isupper()
    return not name.startswith("_")


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------

def detect_god_nodes(
    relationships: list,
    symbols: list | None = None,
    config: RefactorConfig | None = None,
) -> list[RefactorIssue]:
    """Detect god classes/functions: top ``config.god_node_top_pct`` by total degree."""
    if config is None:
        config = RefactorConfig()

    in_deg: dict[str, int] = defaultdict(int)
    out_deg: dict[str, int] = defaultdict(int)
    callers_of: dict[str, list[str]] = defaultdict(list)

    for rel in relationships:
        frm = _get_from(rel)
        to = _get_to(rel)
        if frm:
            out_deg[frm] += 1
        if to:
            in_deg[to] += 1
            if frm:
                callers_of[to].append(frm)

    all_nodes = set(in_deg) | set(out_deg)
    if not all_nodes:
        return []

    scored = sorted(all_nodes, key=lambda n: in_deg[n] + out_deg[n], reverse=True)
    threshold = max(1, int(len(scored) * config.god_node_top_pct))
    god_nodes = scored[:threshold]

    sym_lookup = _build_sym_lookup(symbols)

    issues: list[RefactorIssue] = []
    for name in god_nodes:
        sym = sym_lookup.get(name)
        issues.append(RefactorIssue(
            kind="god_class",
            symbol=name,
            file=_sym_file(sym) if sym is not None else "",
            severity="high",
            metrics={
                "in_degree": in_deg[name],
                "out_degree": out_deg[name],
                "total_degree": in_deg[name] + out_deg[name],
            },
            callers=list(callers_of.get(name, [])),
        ))
    return issues


def detect_circular_deps(relationships: list) -> list[RefactorIssue]:
    """Detect circular dependencies using DFS cycle detection."""
    graph: dict[str, list[str]] = defaultdict(list)
    all_nodes: set[str] = set()

    for rel in relationships:
        frm = _get_from(rel)
        to = _get_to(rel)
        if frm and to and frm != to:
            graph[frm].append(to)
            all_nodes.add(frm)
            all_nodes.add(to)

    # Sort adjacency lists for deterministic output
    for k in graph:
        graph[k].sort()

    visited: set[str] = set()
    in_stack: set[str] = set()
    path: list[str] = []
    found_cycles: list[list[str]] = []
    seen_cycle_keys: set[str] = set()

    def _dfs(node: str) -> None:
        visited.add(node)
        in_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                _dfs(neighbor)
            elif neighbor in in_stack:
                # Locate cycle start in current path
                idx = next((i for i, p in enumerate(path) if p == neighbor), -1)
                if idx >= 0:
                    cycle = list(path[idx:])
                    # Normalise: rotate so lexicographically smallest node is first
                    min_idx = cycle.index(min(cycle))
                    normalized = tuple(cycle[min_idx:] + cycle[:min_idx])
                    key = "->".join(normalized)
                    if key not in seen_cycle_keys:
                        seen_cycle_keys.add(key)
                        found_cycles.append(cycle)

        path.pop()
        in_stack.discard(node)

    for node in sorted(all_nodes):
        if node not in visited:
            _dfs(node)

    issues: list[RefactorIssue] = []
    for cycle in found_cycles:
        cycle_str = " -> ".join(cycle) + f" -> {cycle[0]}"
        issues.append(RefactorIssue(
            kind="circular_dep",
            symbol=cycle[0],
            file="",
            severity="high",
            metrics={"cycle_length": len(cycle), "cycle": cycle_str},
            callers=cycle[1:],
        ))
    return issues


def detect_dead_code(relationships: list, symbols: list) -> list[RefactorIssue]:
    """Detect dead code: symbols with zero in-degree that are not exported/public."""
    in_deg: dict[str, int] = defaultdict(int)
    for rel in relationships:
        to = _get_to(rel)
        if to:
            in_deg[to] += 1

    issues: list[RefactorIssue] = []
    for sym in symbols:
        name = _sym_name(sym)
        file_ = _sym_file(sym)
        kind = _sym_kind(sym)
        if not name:
            continue
        if in_deg[name] > 0:
            continue
        if _is_exported(name, file_):
            continue
        issues.append(RefactorIssue(
            kind="dead_code",
            symbol=name,
            file=file_,
            severity="low",
            metrics={"in_degree": 0, "kind": kind},
            callers=[],
        ))
    return issues


def detect_high_fan_in(
    relationships: list,
    symbols: list | None = None,
    config: RefactorConfig | None = None,
) -> list[RefactorIssue]:
    """Detect symbols with high fan-in (more than ``config.high_fan_in`` callers)."""
    if config is None:
        config = RefactorConfig()

    in_deg: dict[str, int] = defaultdict(int)
    callers_of: dict[str, list[str]] = defaultdict(list)

    for rel in relationships:
        frm = _get_from(rel)
        to = _get_to(rel)
        if to:
            in_deg[to] += 1
            if frm:
                callers_of[to].append(frm)

    sym_lookup = _build_sym_lookup(symbols)

    issues: list[RefactorIssue] = []
    for name, count in in_deg.items():
        if count > config.high_fan_in:
            sym = sym_lookup.get(name)
            issues.append(RefactorIssue(
                kind="high_fan_in",
                symbol=name,
                file=_sym_file(sym) if sym is not None else "",
                severity="medium",
                metrics={"in_degree": count},
                callers=list(callers_of.get(name, [])),
            ))
    return issues


def detect_high_fan_out(
    relationships: list,
    symbols: list | None = None,
    config: RefactorConfig | None = None,
) -> list[RefactorIssue]:
    """Detect symbols with high fan-out (more than ``config.high_fan_out`` dependencies)."""
    if config is None:
        config = RefactorConfig()

    out_deg: dict[str, int] = defaultdict(int)
    deps_of: dict[str, list[str]] = defaultdict(list)

    for rel in relationships:
        frm = _get_from(rel)
        to = _get_to(rel)
        if frm:
            out_deg[frm] += 1
            if to:
                deps_of[frm].append(to)

    sym_lookup = _build_sym_lookup(symbols)

    issues: list[RefactorIssue] = []
    for name, count in out_deg.items():
        if count > config.high_fan_out:
            sym = sym_lookup.get(name)
            issues.append(RefactorIssue(
                kind="high_fan_out",
                symbol=name,
                file=_sym_file(sym) if sym is not None else "",
                severity="medium",
                metrics={"out_degree": count},
                callers=list(deps_of.get(name, [])),
            ))
    return issues


def detect_deep_inheritance(
    relationships: list,
    symbols: list | None = None,
    config: RefactorConfig | None = None,
) -> list[RefactorIssue]:
    """Detect deep inheritance chains (depth > ``config.deep_inheritance_depth``)."""
    if config is None:
        config = RefactorConfig()

    # child -> list of parents
    inherits_graph: dict[str, list[str]] = defaultdict(list)
    for rel in relationships:
        if _get_kind(rel) == "inherits":
            frm = _get_from(rel)
            to = _get_to(rel)
            if frm and to:
                inherits_graph[frm].append(to)

    sym_lookup = _build_sym_lookup(symbols)

    def _depth(name: str, visiting: set[str]) -> int:
        if name in visiting:
            return 0  # cycle guard
        parents = inherits_graph.get(name, [])
        if not parents:
            return 0
        visiting.add(name)
        d = 1 + max(_depth(p, visiting) for p in parents)
        visiting.discard(name)
        return d

    issues: list[RefactorIssue] = []
    for name in list(inherits_graph.keys()):
        depth = _depth(name, set())
        if depth > config.deep_inheritance_depth:
            sym = sym_lookup.get(name)
            # Walk first-parent chain for display
            chain = [name]
            node = name
            for _ in range(depth):
                parents = inherits_graph.get(node, [])
                if not parents:
                    break
                node = parents[0]
                chain.append(node)
            issues.append(RefactorIssue(
                kind="deep_inheritance",
                symbol=name,
                file=_sym_file(sym) if sym is not None else "",
                severity="medium",
                metrics={"depth": depth, "chain": " -> ".join(chain)},
                callers=[],
            ))
    return issues


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def detect_all(
    relationships: list,
    symbols: list | None = None,
    config: RefactorConfig | None = None,
) -> list[RefactorIssue]:
    """Run all refactor checks and return the combined list of issues."""
    if config is None:
        config = RefactorConfig()
    syms = symbols or []
    issues: list[RefactorIssue] = []
    issues.extend(detect_god_nodes(relationships, syms, config))
    issues.extend(detect_circular_deps(relationships))
    issues.extend(detect_dead_code(relationships, syms))
    issues.extend(detect_high_fan_in(relationships, syms, config))
    issues.extend(detect_high_fan_out(relationships, syms, config))
    issues.extend(detect_deep_inheritance(relationships, syms, config))
    return issues
