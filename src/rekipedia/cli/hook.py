"""rekipedia hook CLI — install/uninstall/status git post-commit hook."""
from __future__ import annotations

import stat
from datetime import datetime
from pathlib import Path

import click

HOOK_MARKER = "# rekipedia-managed hook"
HOOK_SCRIPT = """\
#!/bin/sh
# rekipedia-managed hook
# Do not edit this block manually
rekipedia update . --quiet > /dev/null 2>&1 &
"""


def _find_git_dir() -> Path | None:
    """Walk up from cwd to find .git directory."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        git_dir = parent / ".git"
        if git_dir.is_dir():
            return git_dir
    return None


@click.group("hook")
def hook_cmd() -> None:
    """Manage git hooks for automatic wiki rebuilds."""


@hook_cmd.command("install")
def install() -> None:
    """Install a post-commit hook that auto-rebuilds the wiki."""
    git_dir = _find_git_dir()
    if git_dir is None:
        raise click.ClickException("No .git directory found in current or parent directories.")

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    hook_path = hooks_dir / "post-commit"

    hook_path.write_text(HOOK_SCRIPT)
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    click.echo(f"✓ rekipedia post-commit hook installed at {hook_path}")


@hook_cmd.command("uninstall")
def uninstall() -> None:
    """Uninstall the rekipedia post-commit hook."""
    git_dir = _find_git_dir()
    if git_dir is None:
        raise click.ClickException("No .git directory found in current or parent directories.")

    hook_path = git_dir / "hooks" / "post-commit"

    if not hook_path.exists():
        click.echo("No post-commit hook found.")
        return

    content = hook_path.read_text()
    if HOOK_MARKER not in content:
        raise click.ClickException(
            "post-commit hook exists but was not installed by rekipedia. Aborting."
        )

    hook_path.unlink()
    click.echo("✓ rekipedia post-commit hook removed.")


@hook_cmd.command("status")
def status() -> None:
    """Show whether the rekipedia post-commit hook is installed."""
    git_dir = _find_git_dir()
    if git_dir is None:
        click.echo("Not inside a git repository.")
        return

    hook_path = git_dir / "hooks" / "post-commit"

    if not hook_path.exists():
        click.echo("Hook status: not installed")
        return

    content = hook_path.read_text()
    if HOOK_MARKER not in content:
        click.echo("Hook status: installed (not managed by rekipedia)")
        return

    mtime = datetime.fromtimestamp(hook_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    click.echo("Hook status: installed (rekipedia-managed)")
    click.echo(f"Last modified: {mtime}")
    click.echo(f"Path: {hook_path}")
