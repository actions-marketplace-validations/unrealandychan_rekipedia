"""Tests for reki diff command (snapshot-based)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from rekipedia.cli.diff import diff_cmd
from rekipedia.orchestrator.snapshot import save_snapshot, SNAPSHOT_DIR_NAME
from rekipedia.models.contracts import AnalysisResult


def _make_result(symbols=None, relationships=None):
    return AnalysisResult(
        shard_id="all",
        files_seen=[],
        entry_points=[],
        symbols=symbols or [],
        relationships=relationships or [],
        build_commands=[],
        test_commands=[],
        risks=[],
    )


def test_diff_requires_two_snapshots(tmp_path):
    """diff aborts if fewer than 2 snapshots and no explicit paths given."""
    runner = CliRunner()
    result = runner.invoke(diff_cmd, ["--output-dir", str(tmp_path)])
    assert result.exit_code != 0


def test_diff_with_two_snapshots(tmp_path):
    """diff succeeds when two snapshots exist."""
    r1 = _make_result()
    r2 = _make_result()
    save_snapshot(r1, tmp_path)
    save_snapshot(r2, tmp_path)

    runner = CliRunner()
    result = runner.invoke(diff_cmd, ["--output-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "Comparing" in result.output


def test_diff_shows_summary_table(tmp_path):
    """diff shows a summary table."""
    save_snapshot(_make_result(), tmp_path)
    save_snapshot(_make_result(), tmp_path)

    runner = CliRunner()
    result = runner.invoke(diff_cmd, ["--output-dir", str(tmp_path)])
    assert result.exit_code == 0
    # Rich table headers appear in output
    assert "symbols" in result.output.lower() or "Graph Diff" in result.output


def test_diff_writes_markdown_out(tmp_path):
    """diff writes markdown when --out is given."""
    save_snapshot(_make_result(), tmp_path)
    save_snapshot(_make_result(), tmp_path)

    out_file = tmp_path / "diff.md"
    runner = CliRunner()
    result = runner.invoke(diff_cmd, ["--output-dir", str(tmp_path), "--out", str(out_file)])
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text()
    assert "#" in content


def test_diff_explicit_snapshot_paths(tmp_path):
    """diff accepts explicit snapshot file paths."""
    p1 = save_snapshot(_make_result(), tmp_path)
    p2 = save_snapshot(_make_result(), tmp_path)

    runner = CliRunner()
    result = runner.invoke(diff_cmd, [str(p1), str(p2)])
    assert result.exit_code == 0
    assert "Comparing" in result.output
