"""Tests for scan progress display (shard count + ETA) — closes #37."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rekipedia.models.contracts import LLMConfig
from rekipedia.orchestrator.run_digest import run_digest

MINI_PY = Path(__file__).parent / "fixtures" / "mini-py-repo"


def _fake_llm_response(slug: str = "index") -> str:
    import json

    return json.dumps(
        {
            "title": slug.title(),
            "summary": "Stub summary.",
            "key_concepts": [],
            "symbols": [],
            "relationships": [],
            "risks": [],
            "build_commands": [],
            "test_commands": [],
            "mermaid_graph": "",
        }
    )


@pytest.fixture()
def mock_llm():
    with patch("rekipedia.synthesis.page_builder.LLMClient") as MockClient:
        mock_instance = MagicMock()
        mock_instance.call.side_effect = lambda prompt, system="": _fake_llm_response()
        MockClient.return_value = mock_instance
        yield mock_instance


def test_progress_callback_called_during_scan(mock_llm, tmp_path):
    """Progress callback must be invoked at least once during a full scan."""
    output_dir = tmp_path / ".rekipedia"
    calls: list[str] = []

    run_digest(
        repo_root=MINI_PY,
        output_dir=output_dir,
        llm_config=LLMConfig(),
        force_local=True,
        progress=calls.append,
    )

    assert len(calls) > 0, "Progress callback was never called"


def test_shard_count_in_progress(mock_llm, tmp_path):
    """Progress callback messages must include 'Shard X/N' format."""
    output_dir = tmp_path / ".rekipedia"
    calls: list[str] = []

    run_digest(
        repo_root=MINI_PY,
        output_dir=output_dir,
        llm_config=LLMConfig(),
        force_local=True,
        progress=calls.append,
    )

    shard_msgs = [m for m in calls if m.startswith("Shard ") and "/" in m]
    assert len(shard_msgs) > 0, (
        f"No 'Shard X/N' messages found in progress calls: {calls}"
    )
    # Verify format is "Shard X/N" with numeric values
    for msg in shard_msgs:
        parts = msg.split(" ")[1].split("/")
        assert len(parts) == 2, f"Unexpected shard message format: {msg}"
        assert parts[0].isdigit() and parts[1].isdigit(), (
            f"Non-numeric shard counts in: {msg}"
        )


def test_progress_does_not_crash_without_callback(mock_llm, tmp_path):
    """run_digest must complete successfully when progress=None (the default)."""
    output_dir = tmp_path / ".rekipedia"

    # Should not raise
    run_digest(
        repo_root=MINI_PY,
        output_dir=output_dir,
        llm_config=LLMConfig(),
        force_local=True,
        progress=None,
    )

    wiki_dir = output_dir / "wiki"
    assert wiki_dir.exists(), "Wiki directory should be created even without progress callback"


def test_page_progress_fires(mock_llm, tmp_path):
    """Progress callback must include 'Page X/N' messages during wiki synthesis."""
    output_dir = tmp_path / ".rekipedia"
    calls: list[str] = []

    run_digest(
        repo_root=MINI_PY,
        output_dir=output_dir,
        llm_config=LLMConfig(),
        force_local=True,
        progress=calls.append,
    )

    page_msgs = [m for m in calls if m.startswith("Page ") and "/" in m]
    assert len(page_msgs) > 0, (
        f"No 'Page X/N' messages found in progress calls: {calls}"
    )
    for msg in page_msgs:
        parts = msg.split(" ")[1].split("/")
        assert len(parts) == 2, f"Unexpected page message format: {msg}"
        assert parts[0].isdigit() and parts[1].isdigit(), (
            f"Non-numeric page counts in: {msg}"
        )
