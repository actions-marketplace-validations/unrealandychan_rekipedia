"""Tests for rationale note extraction and RationaleNote model."""
from __future__ import annotations

import re

import pytest

from rekipedia.models.contracts import RationaleNote

RATIONALE_RE = re.compile(r"#\s*(NOTE|IMPORTANT|HACK|WHY|TODO):\s*(.*)", re.IGNORECASE)

SAMPLE_SOURCE = """\
def foo():
    # NOTE: this is important
    x = 1
    # HACK: workaround for bug #123
    y = x + 1
    # WHY: we do it this way because of legacy reasons
    return y
"""


def extract_rationale(source: str) -> list[dict]:
    notes = []
    for i, line in enumerate(source.splitlines(), start=1):
        m = RATIONALE_RE.search(line)
        if m:
            notes.append({"tag": m.group(1).upper(), "content": m.group(2).strip(), "line": i})
    return notes


def test_python_extractor_finds_note() -> None:
    notes = extract_rationale(SAMPLE_SOURCE)
    tags = [n["tag"] for n in notes]
    assert "NOTE" in tags


def test_python_extractor_finds_hack() -> None:
    notes = extract_rationale(SAMPLE_SOURCE)
    tags = [n["tag"] for n in notes]
    assert "HACK" in tags


def test_python_extractor_finds_why() -> None:
    notes = extract_rationale(SAMPLE_SOURCE)
    tags = [n["tag"] for n in notes]
    assert "WHY" in tags


def test_rationale_note_model_validates() -> None:
    note = RationaleNote(tag="NOTE", content="important thing", file="foo.py", line=5)
    assert note.tag == "NOTE"
    assert note.line == 5


def test_rationale_note_model_rejects_invalid_tag() -> None:
    with pytest.raises(Exception):
        RationaleNote(tag="INVALID", content="x", file="f.py", line=1)
