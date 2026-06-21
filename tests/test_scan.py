"""Integration test for rekipedia scan using LocalRunner (no Docker required)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rekipedia.models.contracts import LLMConfig
from rekipedia.orchestrator.run_digest import run_digest

MINI_PY = Path(__file__).parent / "fixtures" / "mini-py-repo"
MINI_TS = Path(__file__).parent / "fixtures" / "mini-ts-repo"


def _fake_llm_response(slug: str = "index") -> str:
    import json
    return json.dumps({
        "title": slug.title(),
        "summary": "Stub summary.",
        "key_concepts": [],
        "symbols": [],
        "relationships": [],
        "risks": [],
        "build_commands": [],
        "test_commands": [],
        "mermaid_graph": "",
    })


@pytest.fixture()
def mock_llm():
    with patch("rekipedia.synthesis.page_builder.LLMClient") as MockClient:
        mock_instance = MagicMock()
        mock_instance.call.side_effect = lambda prompt, system="": _fake_llm_response()
        MockClient.return_value = mock_instance
        yield mock_instance


def test_scan_mini_py_repo(mock_llm, tmp_path):
    output_dir = tmp_path / ".rekipedia"
    run_digest(
        repo_root=MINI_PY,
        output_dir=output_dir,
        llm_config=LLMConfig(),
        force_local=True,
    )

    # Wiki pages created
    wiki_dir = output_dir / "wiki"
    assert wiki_dir.exists()
    pages = list(wiki_dir.glob("*.md"))
    assert len(pages) >= 3

    # Manifest created
    manifest = output_dir / "exports" / "manifest.json"
    assert manifest.exists()

    import json
    data = json.loads(manifest.read_text())
    assert data["file_count"] > 0
    assert len(data["pages"]) >= 3


def test_scan_creates_diagrams(mock_llm, tmp_path):
    output_dir = tmp_path / ".rekipedia"
    run_digest(
        repo_root=MINI_PY,
        output_dir=output_dir,
        llm_config=LLMConfig(),
        force_local=True,
    )
    diagram_dir = output_dir / "diagrams"
    assert diagram_dir.exists()


def test_scan_populates_db(mock_llm, tmp_path):
    output_dir = tmp_path / ".rekipedia"
    run_digest(
        repo_root=MINI_PY,
        output_dir=output_dir,
        llm_config=LLMConfig(),
        force_local=True,
    )
    db_path = output_dir / "store.db"
    assert db_path.exists()

    import sqlite_utils
    db = sqlite_utils.Database(db_path)
    assert db["scan_runs"].count >= 1
    # symbols should be populated (scan_symbols table may or may not have rows)
    assert "scan_runs" in db.table_names()


def test_scan_mini_ts_repo(mock_llm, tmp_path):
    output_dir = tmp_path / ".rekipedia"
    run_digest(
        repo_root=MINI_TS,
        output_dir=output_dir,
        llm_config=LLMConfig(),
        force_local=True,
    )
    manifest = output_dir / "exports" / "manifest.json"
    assert manifest.exists()


def test_scan_and_update_quiet(mock_llm, tmp_path):
    from click.testing import CliRunner
    from rekipedia.cli.scan import scan_cmd
    from rekipedia.cli.update import update_cmd

    output_dir = tmp_path / ".rekipedia"
    runner = CliRunner()

    # 1. Scan with --quiet
    result = runner.invoke(
        scan_cmd,
        [str(MINI_PY), "--output-dir", str(output_dir), "--no-docker", "--quiet"],
    )
    assert result.exit_code == 0
    clean_output = "\n".join(
        line for line in result.output.splitlines()
        if "litellm" not in line.lower() and "feedback" not in line.lower() and "provider" not in line.lower()
    ).strip()
    assert clean_output == ""

    # Ensure output exists
    assert (output_dir / "wiki").exists()

    # 2. Update with --quiet
    result = runner.invoke(
        update_cmd,
        [str(MINI_PY), "--output-dir", str(output_dir), "--no-docker", "--quiet"],
    )
    assert result.exit_code == 0
    clean_output_update = "\n".join(
        line for line in result.output.splitlines()
        if "litellm" not in line.lower() and "feedback" not in line.lower() and "provider" not in line.lower()
    ).strip()
    assert clean_output_update == ""


def test_scan_incremental_skip_unchanged_files(mock_llm, tmp_path):
    import shutil
    from rekipedia.storage.sqlite_store import SqliteStore

    # Copy fixture to tmp_path/repo
    repo = tmp_path / "repo"
    shutil.copytree(MINI_PY, repo)
    output_dir = tmp_path / ".rekipedia"

    # Track how many times get_runner().run is called
    with patch("rekipedia.orchestrator.run_digest.get_runner") as mock_get_runner:
        runner_instance = MagicMock()
        runner_instance.run.side_effect = lambda shard, root: MagicMock(
            shard_id=shard.shard_id,
            files_seen=[f.path for f in shard.files],
            entry_points=[],
            symbols=[],
            relationships=[],
        )
        mock_get_runner.return_value = runner_instance

        # 1st scan - Full scan (since no previous run exists)
        run_digest(
            repo_root=repo,
            output_dir=output_dir,
            llm_config=LLMConfig(),
            force_local=True,
        )
        
        # Check first scan run status in DB
        db = SqliteStore(output_dir / "store.db")
        db.open()
        runs = db.db.execute("SELECT id, status, started_at FROM scan_runs").fetchall()
        print("\n=== RUNS IN DB BEFORE 2ND SCAN ===", runs)
        db.close()

        # Verify run was called (first scan gets sharded and runs)
        assert runner_instance.run.call_count > 0
        runner_instance.run.reset_mock()

        # Mutate a file
        (repo / "utils.py").write_text("# mutated\ndef helper(): pass\n", encoding="utf-8")

        # 2nd scan - Incremental scan
        run_digest(
            repo_root=repo,
            output_dir=output_dir,
            llm_config=LLMConfig(),
            force_local=True,
        )
        
        # Verify run was called only on the changed file
        assert runner_instance.run.call_count == 1
        called_shard = runner_instance.run.call_args[0][0]
        # Shard files should only contain 'utils.py'
        called_paths = {f.path for f in called_shard.files}
        assert called_paths == {"utils.py"}


def test_scan_with_preset_yaml(mock_llm, tmp_path):
    preset_content = """
name: "Clean Architecture Preset"
description: "Preset for clean architecture"
sections:
  - id: "domain"
    title: "Domain Layer"
    pages: ["domain-entities"]
pages:
  - slug: "domain-entities"
    title: "Domain Entities"
    section: "domain"
    importance: 90
    focus: "Document domain entities."
    glob: "**/math_helper.py"
"""
    preset_file = tmp_path / "custom_preset.yml"
    preset_file.write_text(preset_content, encoding="utf-8")

    output_dir = tmp_path / ".rekipedia"
    run_digest(
        repo_root=MINI_PY,
        output_dir=output_dir,
        llm_config=LLMConfig(),
        force_local=True,
        preset=str(preset_file),
    )

    # Only our custom page "domain-entities" should be generated
    wiki_dir = output_dir / "wiki"
    assert wiki_dir.exists()
    pages = sorted(list(wiki_dir.glob("*.md")))
    slugs = [p.stem for p in pages]
    assert "domain-entities" in slugs
    
    # Read manifest to make sure it includes our custom sections and pages
    manifest = output_dir / "exports" / "manifest.json"
    assert manifest.exists()
    import json
    data = json.loads(manifest.read_text())
    assert any(p["slug"] == "domain-entities" for p in data["pages"])



