"""reki affected — git-diff-aware minimal test file selection.

Reads changed files from stdin (e.g. ``git diff --name-only``) or from
``--base``/``--head`` git refs, then uses the stored call graph to compute
the minimum set of test files that need to run.

Usage examples::

    # Pipe git diff
    git diff --name-only | reki affected

    # Compare branches
    reki affected --base main --head feature/my-pr

    # Explicit file list
    reki affected --files src/auth.py,src/models/user.py

    # JSON output for CI scripts
    git diff origin/main --name-only | reki affected --format json
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

console = Console()


def _git_diff_files(base: str, head: str) -> list[str]:
    """Return files changed between two git refs."""
    result = subprocess.run(
        ["git", "diff", "--name-only", base, head],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise click.ClickException(
            f"git diff failed: {result.stderr.strip()}"
        )
    return [l.strip() for l in result.stdout.splitlines() if l.strip()]


def _read_stdin_files() -> list[str]:
    """Read newline-separated file paths from stdin."""
    try:
        if sys.stdin.isatty():
            return []
        return [l.strip() for l in sys.stdin.read().splitlines() if l.strip()]
    except OSError:
        return []


def _resolve_files(
    files_opt: str | None,
    base: str | None,
    head: str | None,
) -> list[str]:
    """Resolve changed files from --files, --base/--head, or stdin."""
    if files_opt:
        return [f.strip() for f in files_opt.split(",") if f.strip()]
    if base:
        return _git_diff_files(base, head or "HEAD")
    stdin = _read_stdin_files()
    if stdin:
        return stdin
    return []


@click.command("affected")
@click.option(
    "--base",
    default=None,
    metavar="REF",
    help="Base git ref (e.g. main, origin/main). Compared against --head.",
)
@click.option(
    "--head",
    default="HEAD",
    show_default=True,
    metavar="REF",
    help="Head git ref (default: HEAD). Used with --base.",
)
@click.option(
    "--files",
    default=None,
    metavar="FILE1,FILE2,...",
    help="Comma-separated list of changed files (alternative to git diff / stdin).",
)
@click.option(
    "--depth",
    default=0,
    show_default=True,
    help="Call-graph traversal depth. 0 = unlimited.",
)
@click.option(
    "--format",
    "output_format",
    default="text",
    type=click.Choice(["text", "json"]),
    show_default=True,
    help="Output format.",
)
@click.option(
    "--output-dir",
    default=".",
    show_default=True,
    help="Directory containing .rekipedia/",
)
@click.option(
    "--include-all",
    is_flag=True,
    default=False,
    help="Include all affected files, not just test files.",
)
def affected_cmd(
    base: str | None,
    head: str,
    files: str | None,
    depth: int,
    output_format: str,
    output_dir: str,
    include_all: bool,
) -> None:
    """Print test files affected by changed source files.

    Reads changed files from:
      1. --files option (comma-separated)
      2. --base / --head git refs
      3. stdin (pipe from git diff --name-only)

    Exits with code 0. Outputs one file path per line (text) or JSON.
    """
    from rekipedia.storage.sqlite_store import SqliteStore
    from rekipedia.analysis.impact import compute_impact

    # ── resolve changed files ──────────────────────────────────────────────
    changed = _resolve_files(files, base, head)
    if not changed:
        if output_format == "json":
            click.echo(json.dumps({"changed_files": [], "affected_tests": [], "affected_files": []}))
        else:
            console.print("[yellow]No changed files provided. Pipe from git diff or use --files / --base.[/yellow]")
        return

    # ── open store ────────────────────────────────────────────────────────
    db_path = Path(output_dir) / ".rekipedia" / "store.db"
    if not db_path.exists():
        alt = Path(output_dir) / ".rekipedia" / "rekipedia.db"
        if alt.exists():
            db_path = alt
    if not db_path.exists():
        raise click.ClickException(
            f"No rekipedia DB at {Path(output_dir) / '.rekipedia' / 'store.db'}. Run `reki scan` first."
        )

    store = SqliteStore(db_path)
    with store:
        run_id = store.get_latest_run_id(str(Path(output_dir).resolve()))
        if not run_id:
            raise click.ClickException("No scan runs found. Run `reki scan` first.")

        symbols = store.get_all_symbols(run_id)
        relationships = store.get_all_relationships(run_id)

    # ── compute impact for all changed files ──────────────────────────────
    _depth = depth if depth > 0 else 999  # 0 = unlimited
    all_tests: set[str] = set()
    all_affected: set[str] = set()
    per_file: dict[str, dict] = {}

    for changed_file in changed:
        result = compute_impact(
            changed_file,
            relationships,
            symbols,
            depth=_depth,
        )
        per_file[changed_file] = result
        all_tests.update(result["related_tests"])
        all_affected.update(result["affected_files"])

    # ── output ────────────────────────────────────────────────────────────
    output_files = sorted(all_affected) if include_all else sorted(all_tests)

    if output_format == "json":
        click.echo(
            json.dumps(
                {
                    "changed_files": changed,
                    "affected_tests": sorted(all_tests),
                    "affected_files": sorted(all_affected),
                    "depth": depth,
                    "per_file": {
                        f: {
                            "related_tests": r["related_tests"],
                            "affected_files": r["affected_files"],
                            "total_affected_symbols": r["total_affected"],
                        }
                        for f, r in per_file.items()
                    },
                },
                indent=2,
            )
        )
    else:
        for f in output_files:
            click.echo(f)

        if not output_files:
            console.print(
                "[dim]No affected test files found for the given changes.[/dim]"
            )
