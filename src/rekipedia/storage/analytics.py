"""Analytics helpers for rekipedia storage."""
from __future__ import annotations


class AnalyticsMixin:
    """Mixin providing analytics/graph operations."""

    def get_god_nodes(self, run_id: str, top_n: int = 10) -> list[tuple[str, int]]:
        """Return top_n god nodes (symbol name, degree) for the given run."""
        from rekipedia.analysis.graph_analysis import compute_god_nodes

        rels = self.get_relationships_for_run(run_id)

        class _Rel:
            __slots__ = ("from_", "to")

            def __init__(self, d: dict) -> None:
                self.from_ = d["from_"]
                self.to = d["to"]

        return compute_god_nodes([_Rel(r) for r in rels], top_n=top_n)
