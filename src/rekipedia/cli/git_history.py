"""rekipedia git-history — parse and populate git commit history."""
from __future__ import annotations

from pathlib import Path
import click
from rich.console import Console

console = Console()


@click.command("git-history")
@click.argument("repo", default=".", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--limit", default=100, show_default=True, help="Number of recent commits to analyze")
def git_history_cmd(repo: Path, limit: int) -> None:
    """Parse git log and populate commit and file changes in database."""
    from rekipedia.storage.sqlite_store import SqliteStore
    from rekipedia.analysis.git_history import extract_git_history, save_git_history

    repo = repo.resolve()
    db_path = repo / ".rekipedia" / "store.db"
    if not db_path.exists():
        alt = repo / ".rekipedia" / "rekipedia.db"
        if alt.exists():
            db_path = alt
    if not db_path.exists():
        console.print(f"[red]No rekipedia DB at {db_path}. Run `reki scan` first.[/red]")
        raise click.Abort()

    with SqliteStore(db_path) as store:
        run_id = store.get_latest_run_id(str(repo))
        if not run_id:
            console.print("[red]No scan runs found.[/red]")
            raise click.Abort()

        console.print(f"⌛ Parsing last {limit} git commits from {repo}...")
        commits = extract_git_history(repo, run_id, limit=limit)
        if not commits:
            console.print("[red]No git history found or not a git repository.[/red]")
            return

        save_git_history(store, run_id, commits)
        console.print(f"[green]✅ Saved {len(commits)} commits to database.[/green]")
