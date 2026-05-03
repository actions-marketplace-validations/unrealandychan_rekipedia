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
