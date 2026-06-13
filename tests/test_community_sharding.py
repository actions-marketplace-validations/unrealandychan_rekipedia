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
