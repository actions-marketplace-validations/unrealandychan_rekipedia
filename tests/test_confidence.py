"""Tests for Relationship confidence and evidence_tag fields."""
from __future__ import annotations

from rekipedia.models.contracts import Relationship


def test_relationship_default_confidence() -> None:
    rel = Relationship(**{"from": "A", "to": "B", "kind": "call"})
    assert rel.confidence == 1.0


def test_relationship_default_evidence_tag() -> None:
    rel = Relationship(**{"from": "A", "to": "B", "kind": "call"})
    assert rel.evidence_tag == "EXTRACTED"


def test_relationship_accepts_confidence() -> None:
    rel = Relationship(**{"from": "A", "to": "B", "kind": "call", "confidence": 0.7})
    assert rel.confidence == 0.7


def test_relationship_accepts_evidence_tag_inferred() -> None:
    rel = Relationship(**{"from": "A", "to": "B", "kind": "call", "evidence_tag": "INFERRED"})
    assert rel.evidence_tag == "INFERRED"


def test_relationship_accepts_evidence_tag_ambiguous() -> None:
    rel = Relationship(**{"from": "A", "to": "B", "kind": "call", "evidence_tag": "AMBIGUOUS"})
    assert rel.evidence_tag == "AMBIGUOUS"
