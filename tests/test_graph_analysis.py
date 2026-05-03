"""Tests for graph_analysis.compute_god_nodes."""
from __future__ import annotations

from rekipedia.analysis.graph_analysis import compute_god_nodes
from rekipedia.models.contracts import Relationship


def _rel(from_: str, to: str) -> Relationship:
    return Relationship(**{"from": from_, "to": to, "kind": "call", "file": None})


def test_compute_god_nodes_returns_top_nodes() -> None:
    rels = [
        _rel("A", "B"),
        _rel("A", "C"),
        _rel("D", "A"),
        _rel("B", "C"),
    ]
    result = compute_god_nodes(rels, top_n=3)
    names = [name for name, _ in result]
    # A appears 3 times (2 out + 1 in), C appears 2 times
    assert names[0] == "A"
    assert len(result) <= 3


def test_compute_god_nodes_empty() -> None:
    result = compute_god_nodes([], top_n=10)
    assert result == []


def test_compute_god_nodes_degree_counting() -> None:
    rels = [
        _rel("X", "Y"),
        _rel("X", "Z"),
        _rel("W", "X"),
    ]
    result = compute_god_nodes(rels, top_n=10)
    by_name = dict(result)
    # X: 2 out + 1 in = 3
    assert by_name["X"] == 3
    # Y: 1 in
    assert by_name["Y"] == 1
