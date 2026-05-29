from pathlib import Path

import click
from rich.console import Console

console = Console()

@click.group('watch')
def watch_cmd():
    """Multi-repo daemon — watch directories and auto-index on change."""
    pass

@watch_cmd.command('add')
@click.argument('path')
def watch_add(path):
    """Register a repo to watch."""
    from rekipedia.watcher.watcher import add_repo
    add_repo(path)

@watch_cmd.command('remove')
@click.argument('path')
def watch_remove(path):
    """Unregister a repo."""
    from rekipedia.watcher.watcher import remove_repo
    remove_repo(path)

@watch_cmd.command('list')
def watch_list():
    """List registered repos."""
    from rekipedia.watcher.watcher import list_repos
    repos = list_repos()
    if not repos:
        console.print('[dim]No repos registered.[/dim]')
    for r in repos:
        console.print(f'  [cyan]{r}[/cyan]')

@watch_cmd.command('start')
@click.argument('path', default=None, required=False)
@click.option('--debounce', default=2.0, show_default=True, help='Debounce delay in seconds before triggering update.')
@click.option('--publish/--no-publish', default=None, help='Auto-publish after each incremental update.')
def watch_start(path, debounce, publish):
    """Start the file watcher daemon.

    Optionally pass a PATH to watch directly without registering it first.
    If no PATH is given, watches all registered repos (reki watch add <path>).

    Use --publish to auto-publish the wiki after each update.
    The publish target is resolved from team.sync_dir, then team.publish_dir in config.
    """
    from rekipedia.watcher.watcher import start_watching
    from rekipedia.config.loader import load_config

    repos = [str(Path(path).resolve())] if path else None

    # Resolve publish dir and hook
    post_update_hook = None
    repo_root = Path(path).resolve() if path else Path.cwd()
    cfg = load_config(repo_root)
    team_cfg = cfg.get("team", {})

    auto_watch_publish = team_cfg.get("auto_watch_publish", False)
    enable_publish = publish or auto_watch_publish

    if enable_publish:
        sync_dir = team_cfg.get("sync_dir", "")
        publish_dir = team_cfg.get("publish_dir", "")
        effective_dir = sync_dir or publish_dir

        if not effective_dir:
            console.print("[yellow]⚠ --publish enabled but no publish dir configured (set team.sync_dir or team.publish_dir).[/yellow]")
        else:
            output_dir = repo_root / ".rekipedia"

            def _make_hook(rr: Path, od: Path, pd: str):
                def hook():
                    from rekipedia.orchestrator.run_digest import _auto_publish
                    _auto_publish(rr, od, pd)
                    console.print(f"[green]✔ published[/] {pd}")
                return hook

            post_update_hook = _make_hook(repo_root, output_dir, effective_dir)

    start_watching(repos=repos, debounce_seconds=debounce, post_update_hook=post_update_hook)
