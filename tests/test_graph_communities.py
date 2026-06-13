"""Tests for graph community detection."""
from __future__ import annotations

import pytest

from rekipedia.analysis.graph_communities import detect_communities


def test_empty_graph_returns_empty() -> None:
    assert detect_communities([]) == {}


def test_single_node_self_loop() -> None:
    # Self-loop only → node present with its own community
    result = detect_communities([("A", "A")])
    assert "A" in result


def test_two_strongly_connected_nodes_same_community() -> None:
    edges = [("A", "B"), ("B", "A")]
    result = detect_communities(edges)
    assert result["A"] == result["B"]


def test_two_disconnected_clusters() -> None:
    # A↔B disconnected from C↔D
    edges = [("A", "B"), ("B", "A"), ("C", "D"), ("D", "C")]
    result = detect_communities(edges)
    assert result["A"] == result["B"]
    assert result["C"] == result["D"]
    assert result["A"] != result["C"]


def test_returns_stable_community_ids() -> None:
    # Same input → same output (deterministic)
    edges = [("A", "B"), ("B", "C"), ("C", "A")]
    assert detect_communities(edges) == detect_communities(edges)


def test_returns_integer_community_ids() -> None:
    edges = [("X", "Y")]
    result = detect_communities(edges)
    for v in result.values():
        assert isinstance(v, int)


def test_all_nodes_present_in_result() -> None:
    edges = [("A", "B"), ("C", "D")]
    result = detect_communities(edges)
    assert set(result.keys()) == {"A", "B", "C", "D"}


def test_star_topology_same_community() -> None:
    # Hub H connected to A, B, C — all should be in same community
    edges = [("H", "A"), ("H", "B"), ("H", "C"), ("A", "H"), ("B", "H"), ("C", "H")]
    result = detect_communities(edges)
    assert result["H"] == result["A"] == result["B"] == result["C"]
