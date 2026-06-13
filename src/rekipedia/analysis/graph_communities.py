"""Pure-Python label-propagation community detection for rekipedia.

No external graph library required — uses a label-propagation
approach that converges in O(V+E) per pass for sparse graphs.
Communities are stable (deterministic) because node iteration
order is sorted lexicographically.
"""
from __future__ import annotations

from collections import defaultdict


def detect_communities(edges: list[tuple[str, str]]) -> dict[str, int]:
    """Assign community IDs to nodes via label propagation.

    Treats the directed edge list as undirected for the purpose of
    community detection (import A→B means A and B are related).
    Self-loops are ignored when computing neighbours but the node
    is still included in the result.

    Args:
        edges: List of ``(from_node, to_node)`` string tuples.
               Self-loops (A, A) are accepted but ignored as edges.

    Returns:
        Dict mapping node_name → community_id (int, 0-indexed).
        Returns empty dict for empty input.
    """
    if not edges:
        return {}

    # Build adjacency list (undirected — ignore self-loops)
    neighbours: dict[str, set[str]] = defaultdict(set)
    all_nodes: set[str] = set()
    for frm, to in edges:
        all_nodes.add(frm)
        all_nodes.add(to)
        if frm != to:
            neighbours[frm].add(to)
            neighbours[to].add(frm)

    # Initialise: each node labels itself
    labels: dict[str, str] = {n: n for n in all_nodes}

    # Label propagation — up to 20 passes or until stable
    for _ in range(20):
        changed = False
        # Sorted iteration → deterministic tiebreaking
        for node in sorted(all_nodes):
            nbrs = neighbours[node]
            if not nbrs:
                continue
            # Count neighbour labels
            freq: dict[str, int] = defaultdict(int)
            for nb in nbrs:
                freq[labels[nb]] += 1
            # Pick most-frequent label; break ties by lexicographic minimum
            best_count = max(freq.values())
            candidates = [lbl for lbl, cnt in freq.items() if cnt == best_count]
            best = min(candidates)
            if labels[node] != best:
                labels[node] = best
                changed = True
        if not changed:
            break

    # Convert string labels → stable integer IDs (sorted → 0-indexed)
    unique_labels = sorted(set(labels.values()))
    label_to_id = {lbl: i for i, lbl in enumerate(unique_labels)}
    return {node: label_to_id[labels[node]] for node in all_nodes}
