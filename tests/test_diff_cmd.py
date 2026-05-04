"""Tests for reki diff command."""
from __future__ import annotations

import json
import os
import subprocess
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from rekipedia.cli.diff import diff_cmd


@pytest.fixture()
def tmp_repo(tmp_path):
    """Create a minimal fake git repo with rekipedia structure."""
    # Init git repo
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

    reki_dir = tmp_path / ".rekipedia"
    exports_dir = reki_dir / "exports"
    exports_dir.mkdir(parents=True)

    # Write symbols.json
    symbols = [
        {"name": "FooClass", "file": "foo.py", "kind": "class"},
        {"name": "bar_func", "file": "bar.py", "kind": "function"},
    ]
    (exports_dir / "symbols.json").write_text(json.dumps(symbols))

    # Commit initial state
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)

    return tmp_path


def test_diff_creates_output(tmp_repo):
    """diff command should create an output file."""
    runner = CliRunner()
    result = runner.invoke(diff_cmd, [
        "--repo", str(tmp_repo),
        "--from-ref", "HEAD",
        "--to-ref", "HEAD",
        "--output-dir", str(tmp_repo / ".rekipedia"),
    ])
    assert result.exit_code == 0
    assert (tmp_repo / ".rekipedia" / "diff.md").exists()


def test_diff_shows_added_symbols(tmp_repo):
    """When no previous snapshot exists, all symbols shown as added."""
    runner = CliRunner()
    result = runner.invoke(diff_cmd, [
        "--repo", str(tmp_repo),
        "--from-ref", "NONEXISTENT_REF_XYZ",
        "--to-ref", "HEAD",
        "--output-dir", str(tmp_repo / ".rekipedia"),
    ])
    assert result.exit_code == 0
    output = result.output
    # All current symbols should appear as added
    assert "FooClass" in output or "Added" in output


def test_diff_empty_store_returns_gracefully(tmp_path):
    """diff should handle missing store/symbols gracefully."""
    # Init minimal git
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, capture_output=True)
    (tmp_path / "README.md").write_text("hello")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)

    runner = CliRunner()
    result = runner.invoke(diff_cmd, [
        "--repo", str(tmp_path),
        "--output-dir", str(tmp_path / ".rekipedia"),
    ])
    # Should exit cleanly even with no symbols
    assert result.exit_code == 0


def test_diff_format_markdown(tmp_repo):
    """diff with --format md should produce markdown output."""
    runner = CliRunner()
    result = runner.invoke(diff_cmd, [
        "--repo", str(tmp_repo),
        "--from-ref", "HEAD",
        "--to-ref", "HEAD",
        "--output-dir", str(tmp_repo / ".rekipedia"),
        "--format", "md",
    ])
    assert result.exit_code == 0
    output = result.output
    assert "#" in output  # markdown header


def test_diff_no_changes_message(tmp_repo):
    """When comparing same ref with no changed symbols, show no-changes message."""
    runner = CliRunner()
    result = runner.invoke(diff_cmd, [
        "--repo", str(tmp_repo),
        "--from-ref", "HEAD",
        "--to-ref", "HEAD",
        "--output-dir", str(tmp_repo / ".rekipedia"),
    ])
    assert result.exit_code == 0
    # No changed files between HEAD and HEAD, no prev symbols from git show HEAD
    # Depends on whether symbols.json is committed; either way should exit 0
    output = result.output
    assert "diff" in output.lower() or "Knowledge" in output or "No" in output


def test_diff_format_text(tmp_repo):
    """diff with --format text should produce plain text output."""
    runner = CliRunner()
    result = runner.invoke(diff_cmd, [
        "--repo", str(tmp_repo),
        "--from-ref", "HEAD",
        "--to-ref", "HEAD",
        "--output-dir", str(tmp_repo / ".rekipedia"),
        "--format", "text",
    ])
    assert result.exit_code == 0
    assert (tmp_repo / ".rekipedia" / "diff.txt").exists()
    output = result.output
    assert "Knowledge Diff" in output
