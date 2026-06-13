"""Integration tests for --community-sharding flag."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_run_digest_accepts_community_sharding_flag(tmp_path: Path) -> None:
    """run_digest with community_sharding=True should not raise TypeError."""
    from rekipedia.orchestrator.run_digest import run_digest
    from rekipedia.models.contracts import LLMConfig

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "hello.py").write_text("def hello(): pass\n")

    out_dir = tmp_path / ".rekipedia"

    # Patch the sandbox runner so we don't need Docker/LLM
    with patch("rekipedia.orchestrator.run_digest.get_runner") as mock_runner_factory:
        mock_runner = MagicMock()
        mock_runner.run.return_value = None
        mock_runner_factory.return_value = mock_runner

        # Should not raise TypeError: unexpected keyword argument 'community_sharding'
        try:
            run_digest(
                repo_root=repo,
                output_dir=out_dir,
                llm_config=LLMConfig(),
                community_sharding=True,
                no_llm=True,
            )
        except TypeError as exc:
            pytest.fail(f"run_digest does not accept community_sharding: {exc}")


def test_run_digest_community_sharding_false_by_default(tmp_path: Path) -> None:
    """run_digest without community_sharding should work normally (default=False)."""
    from rekipedia.orchestrator.run_digest import run_digest
    from rekipedia.models.contracts import LLMConfig

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("x = 1\n")

    out_dir = tmp_path / ".rekipedia"

    with patch("rekipedia.orchestrator.run_digest.get_runner") as mock_runner_factory:
        mock_runner = MagicMock()
        mock_runner.run.return_value = None
        mock_runner_factory.return_value = mock_runner

        # Must work without the flag (backward compat)
        try:
            run_digest(
                repo_root=repo,
                output_dir=out_dir,
                llm_config=LLMConfig(),
                no_llm=True,
            )
        except TypeError as exc:
            pytest.fail(f"run_digest broke without community_sharding: {exc}")


def test_community_sharding_uses_real_edges_from_previous_scan(tmp_path: Path) -> None:
    """community_sharding must load import/call edges from the previous scan run,
    NOT fabricate edges from directory proximity."""
    from rekipedia.orchestrator.run_digest import run_digest
    from rekipedia.models.contracts import LLMConfig
    from rekipedia.storage.sqlite_store import SqliteStore

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("import b\n")
    (repo / "b.py").write_text("x = 1\n")
    (repo / "c.py").write_text("y = 2\n")
    out_dir = tmp_path / ".rekipedia"

    with patch("rekipedia.orchestrator.run_digest.get_runner") as mock_runner_factory:
        mock_runner = MagicMock()
        mock_runner.run.return_value = None
        mock_runner_factory.return_value = mock_runner
        # First scan — seeds the DB with a prior run_id
        run_digest(repo_root=repo, output_dir=out_dir, llm_config=LLMConfig(), no_llm=True)

    # Manually seed a real import edge into the previous run
    db_path = out_dir / "store.db"
    store = SqliteStore(db_path)
    store.open()
    prev_run_id = store.get_latest_run_id(str(repo))
    assert prev_run_id is not None, "No successful run found after first scan"
    # Use the public API so the table is created if it doesn't exist yet
    store.upsert_relationships(prev_run_id, [
        {"from_": "a.py", "to": "b.py", "kind": "import", "file": "a.py", "confidence": 1.0, "evidence_tag": "test"},
    ])
    store.close()

    captured_edges: list = []
    import rekipedia.analysis.graph_communities as _gc
    original_detect = _gc.detect_communities

    def spy_detect(edges):
        captured_edges.extend(edges)
        return original_detect(edges)

    with patch("rekipedia.orchestrator.run_digest.get_runner") as mock_runner_factory, \
         patch("rekipedia.analysis.graph_communities.detect_communities", side_effect=spy_detect):
        mock_runner = MagicMock()
        mock_runner.run.return_value = None
        mock_runner_factory.return_value = mock_runner
        run_digest(
            repo_root=repo,
            output_dir=out_dir,
            llm_config=LLMConfig(),
            community_sharding=True,
            no_llm=True,
        )

    # Must have used the real seeded edge
    assert ("a.py", "b.py") in captured_edges, (
        f"Expected real import edge (a.py, b.py) in detect_communities, got: {captured_edges}"
    )
    # Dir-proximity would also produce (b.py, c.py) — real edges should not have it
    assert ("b.py", "c.py") not in captured_edges, (
        "Directory-proximity edge (b.py, c.py) found — still using fake edges"
    )


def test_community_sharding_fallback_on_first_scan(tmp_path: Path) -> None:
    """On first scan (no prior run), community_sharding must fall back gracefully
    and emit a warning rather than crash or silently use fake edges."""
    from rekipedia.orchestrator.run_digest import run_digest
    from rekipedia.models.contracts import LLMConfig

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "x.py").write_text("pass\n")
    out_dir = tmp_path / ".rekipedia"

    progress_msgs: list[str] = []

    with patch("rekipedia.orchestrator.run_digest.get_runner") as mock_runner_factory:
        mock_runner = MagicMock()
        mock_runner.run.return_value = None
        mock_runner_factory.return_value = mock_runner
        try:
            run_digest(
                repo_root=repo,
                output_dir=out_dir,
                llm_config=LLMConfig(),
                community_sharding=True,
                no_llm=True,
                progress=progress_msgs.append,
            )
        except Exception as exc:
            pytest.fail(f"run_digest crashed on first scan with community_sharding: {exc}")

    assert any("prior scan" in m or "fallback" in m.lower() for m in progress_msgs), (
        f"Expected a fallback warning in progress messages, got: {progress_msgs}"
    )


def test_scan_cli_has_community_sharding_option() -> None:
    """The scan CLI command must expose --community-sharding as an option."""
    from click.testing import CliRunner
    from rekipedia.cli.scan import scan_cmd

    runner = CliRunner()
    result = runner.invoke(scan_cmd, ["--help"])
    assert result.exit_code == 0, f"scan --help failed: {result.output}"
    assert "community-sharding" in result.output, (
        "--community-sharding flag not found in scan --help output"
    )
