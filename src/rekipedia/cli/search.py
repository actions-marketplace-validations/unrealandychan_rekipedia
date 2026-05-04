import click
from rich.console import Console
from rich.table import Table

console = Console()

@click.command('search')
@click.argument('query')
@click.option('--output-dir', default='.', show_default=True)
@click.option('--all-repos', is_flag=True, help='Search all registered repos')
def search_cmd(query, output_dir, all_repos):
    """Search symbols in the codebase graph."""
    if all_repos:
        from rekipedia.analysis.cross_repo_search import search_all_repos
        results = search_all_repos(query)
        source = 'all repos'
    else:
        from rekipedia.analysis.cross_repo_search import _search_single_repo
        from pathlib import Path
        db = Path(output_dir) / '.rekipedia' / 'rekipedia.db'
        if not db.exists():
            console.print('[red]No rekipedia DB. Run reki scan first.[/red]')
            raise click.Abort()
        results = _search_single_repo(db, query)
        source = output_dir

    if not results:
        console.print(f'[dim]No results for "{query}" in {source}[/dim]')
        return

    table = Table(title=f'Search: "{query}" ({source})')
    table.add_column('Name', style='cyan')
    table.add_column('Kind', style='dim')
    table.add_column('File', style='dim')
    if all_repos:
        table.add_column('Repo', style='yellow')
    for r in results[:50]:
        row = [r['name'], r['kind'], r['file']]
        if all_repos:
            row.append(r.get('repo', ''))
        table.add_row(*row)
    console.print(table)
