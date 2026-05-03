"""Tests for the hook CLI subcommand."""
from __future__ import annotations

from click.testing import CliRunner

from rekipedia.cli.hook import hook_cmd


def test_hook_help() -> None:
    runner = CliRunner()
    result = runner.invoke(hook_cmd, ["--help"])
    assert result.exit_code == 0


def test_hook_install_subcommand_exists() -> None:
    runner = CliRunner()
    result = runner.invoke(hook_cmd, ["install", "--help"])
    assert result.exit_code == 0


def test_hook_uninstall_subcommand_exists() -> None:
    runner = CliRunner()
    result = runner.invoke(hook_cmd, ["uninstall", "--help"])
    assert result.exit_code == 0


def test_hook_status_subcommand_exists() -> None:
    runner = CliRunner()
    result = runner.invoke(hook_cmd, ["status", "--help"])
    assert result.exit_code == 0
