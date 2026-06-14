"""Tests for the hook CLI subcommand."""
from __future__ import annotations

import os
import stat
from pathlib import Path
from click.testing import CliRunner

from rekipedia.cli.hook import hook_cmd, HOOK_SCRIPT


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


def test_hook_install_uninstall_status_flow() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd_path = Path.cwd()
        
        # 1. Status when not inside git repo
        result = runner.invoke(hook_cmd, ["status"])
        assert result.exit_code == 0
        assert "Not inside a git repository." in result.output

        # Create .git directory to simulate a git repo
        git_dir = cwd_path / ".git"
        git_dir.mkdir()

        # 2. Status when inside git repo but no hook installed
        result = runner.invoke(hook_cmd, ["status"])
        assert result.exit_code == 0
        assert "Hook status: not installed" in result.output

        # 3. Install the hook
        result = runner.invoke(hook_cmd, ["install"])
        assert result.exit_code == 0
        assert "rekipedia post-commit hook installed" in result.output

        hook_path = git_dir / "hooks" / "post-commit"
        assert hook_path.exists()
        
        # Verify content
        content = hook_path.read_text()
        assert HOOK_SCRIPT == content
        
        # Verify executable permissions
        st = hook_path.stat()
        assert bool(st.st_mode & stat.S_IXUSR)

        # 4. Status after installing
        result = runner.invoke(hook_cmd, ["status"])
        assert result.exit_code == 0
        assert "Hook status: installed (rekipedia-managed)" in result.output
        assert str(hook_path) in result.output

        # 5. Uninstall the hook
        result = runner.invoke(hook_cmd, ["uninstall"])
        assert result.exit_code == 0
        assert "rekipedia post-commit hook removed." in result.output
        assert not hook_path.exists()

        # 6. Status after uninstalling
        result = runner.invoke(hook_cmd, ["status"])
        assert result.exit_code == 0
        assert "Hook status: not installed" in result.output


def test_hook_status_non_managed() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd_path = Path.cwd()
        git_dir = cwd_path / ".git"
        git_dir.mkdir()
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir()
        
        hook_path = hooks_dir / "post-commit"
        hook_path.write_text("#!/bin/sh\necho 'custom hook'")

        # 1. Status on custom hook
        result = runner.invoke(hook_cmd, ["status"])
        assert result.exit_code == 0
        assert "Hook status: installed (not managed by rekipedia)" in result.output

        # 2. Uninstall on custom hook should fail/abort
        result = runner.invoke(hook_cmd, ["uninstall"])
        assert result.exit_code != 0
        assert "was not installed by rekipedia. Aborting." in result.output
        assert hook_path.exists()
