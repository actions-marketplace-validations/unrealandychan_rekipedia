"""Tests for reki onboard — onboarding guide generator (#151)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from click.testing import CliRunner

from rekipedia.analysis.onboard import build_onboard_guide
from rekipedia.cli.onboard import onboard_cmd
from rekipedia.storage.sqlite_store import SqliteStore


def _make_store(store_dir: Path, symbols: list[tuple] | None = None, repo_root: Path | None = None) -> Path:
    """Create a minimal store.db via SqliteStore (proper schema + migrations)."""
    db = store_dir / "store.db"
    repo_str = str(repo_root) if repo_root else str(store_dir.parent)
    with SqliteStore(db) as store:
        if symbols:
            run_id = "run1"
            store.upsert_run(run_id, repo_str, status="running")
            sym_dicts = [
                {"name": s[2], "kind": s[3], "file": s[1],
                 "line_start": s[4], "line_end": s[4], "signature": "", "docstring": ""}
                for s in symbols
            ]
            store.upsert_symbols(run_id, sym_dicts)
            store.upsert_run(run_id, repo_str, status="success")
    return db


# ── unit: build_onboard_guide ─────────────────────────────────────────────────

def test_build_onboard_empty_store(tmp_path):
    db = _make_store(tmp_path, repo_root=tmp_path)
    guide = build_onboard_guide(db, tmp_path)
    assert "repo" in guide
    assert "generated_at" in guide
    assert "overview" in guide
    assert "getting_started" in guide
    assert "key_modules" in guide
    assert "architecture" in guide
    assert "patterns" in guide


def test_build_onboard_file_counts(tmp_path):
    symbols = [
        ("run1", "src/a.py", "foo", "function", 1),
        ("run1", "src/a.py", "bar", "function", 10),
        ("run1", "src/a.py", "Baz", "class", 20),
        ("run1", "src/b.py", "qux", "function", 1),
        ("run1", "src/b.py", "quux", "function", 5),
    ]
    db = _make_store(tmp_path, symbols, repo_root=tmp_path)
    guide = build_onboard_guide(db, tmp_path)
    assert guide["_counts"]["files"] == 2
    assert guide["_counts"]["symbols"] == 5
    assert len(guide["key_modules"]) == 2


def test_build_onboard_getting_started_python(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'")
    db = _make_store(tmp_path, repo_root=tmp_path)
    guide = build_onboard_guide(db, tmp_path)
    cmds = [s["cmd"] for s in guide["getting_started"]]
    assert any("pip install" in c for c in cmds)
    assert any("pytest" in c for c in cmds)


def test_build_onboard_getting_started_node(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "x"}')
    db = _make_store(tmp_path, repo_root=tmp_path)
    guide = build_onboard_guide(db, tmp_path)
    cmds = [s["cmd"] for s in guide["getting_started"]]
    assert any("npm install" in c for c in cmds)
    assert any("npm test" in c for c in cmds)


def test_build_onboard_readme_overview(tmp_path):
    (tmp_path / "README.md").write_text(
        "# My Project\n\nThis is the overview paragraph.\n\nMore details here."
    )
    db = _make_store(tmp_path, repo_root=tmp_path)
    guide = build_onboard_guide(db, tmp_path)
    assert "overview paragraph" in guide["overview"]


# ── CLI tests ─────────────────────────────────────────────────────────────────

def test_onboard_cmd_no_scan(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(onboard_cmd, [str(tmp_path)])
    assert result.exit_code == 1
    assert "scan" in result.output.lower() or "scan" in (result.output + "").lower()


def test_onboard_cmd_invalid_scan_schema(tmp_path):
    """SqliteStore auto-migrates any SQLite file, so a pre-existing placeholder table
    is not a fatal error — the guide just returns empty results (no scan run yet)."""
    reki_dir = tmp_path / ".rekipedia"
    reki_dir.mkdir()
    db = sqlite3.connect(str(reki_dir / "store.db"))
    db.execute("CREATE TABLE placeholder (id INTEGER PRIMARY KEY)")
    db.commit()
    db.close()

    runner = CliRunner()
    result = runner.invoke(onboard_cmd, [str(tmp_path)], color=False)
    # Store is valid SQLite; SqliteStore migrates it. Guide runs with 0 symbols.
    assert result.exit_code == 0
    assert "Onboarding Guide" in result.output


def _make_repo_with_store(tmp_path: Path) -> Path:
    reki_dir = tmp_path / ".rekipedia"
    reki_dir.mkdir()
    symbols = [
        ("run1", "src/main.py", "main", "function", 1),
        ("run1", "src/main.py", "helper", "function", 10),
        ("run1", "src/utils.py", "util_fn", "function", 1),
    ]
    _make_store(reki_dir, symbols, repo_root=tmp_path)
    return tmp_path


def test_onboard_cmd_text_output(tmp_path):
    repo = _make_repo_with_store(tmp_path)
    runner = CliRunner()
    result = runner.invoke(onboard_cmd, [str(repo)])
    assert result.exit_code == 0
    assert "Onboarding Guide" in result.output
    assert "Getting Started" in result.output
    assert "Key Modules" in result.output


def test_onboard_cmd_md_output(tmp_path):
    repo = _make_repo_with_store(tmp_path)
    runner = CliRunner()
    result = runner.invoke(onboard_cmd, [str(repo), "--format", "md"])
    assert result.exit_code == 0
    assert "##" in result.output


def test_onboard_cmd_json_output(tmp_path):
    repo = _make_repo_with_store(tmp_path)
    runner = CliRunner()
    result = runner.invoke(onboard_cmd, [str(repo), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "key_modules" in data


def test_onboard_cmd_output_file(tmp_path):
    repo = _make_repo_with_store(tmp_path)
    out_file = tmp_path / "ONBOARDING.md"
    runner = CliRunner()
    result = runner.invoke(onboard_cmd, [str(repo), "--format", "md", "--output", str(out_file)])
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text()
    assert "Onboarding Guide" in content
