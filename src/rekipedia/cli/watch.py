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
def watch_start():
    """Start the file watcher daemon."""
    from rekipedia.watcher.watcher import start_watching
    start_watching()
