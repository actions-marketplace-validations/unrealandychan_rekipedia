"""reki impact — blast-radius analysis for a changed file."""
from __future__ import annotations
import click
from pathlib import Path
from rich.console import Console
from rich.tree import Tree

console = Console()

@click.command("impact")
@click.argument("target_file")
@click.option("--depth", default=2, show_default=True, help="BFS traversal depth")
@click.option("--output-dir", default=".", show_default=True, help="Directory with .rekipedia/")
def impact_cmd(target_file, depth, output_dir):
    """Show blast-radius for a changed file."""
    from rekipedia.storage.sqlite_store import SqliteStore
    from rekipedia.analysis.impact import compute_impact

    db_path = Path(output_dir) / ".rekipedia" / "store.db"
    if not db_path.exists():
        alt = Path(output_dir) / ".rekipedia" / "rekipedia.db"
        if alt.exists():
            db_path = alt
    if not db_path.exists():
        console.print(f"[red]No rekipedia DB at {Path(output_dir) / '.rekipedia' / 'store.db'}. Run reki scan first.[/red]")
        raise click.Abort()

    store = SqliteStore(db_path)
    run_id = store.latest_run_id()
    if not run_id:
        console.print("[red]No scan runs found.[/red]")
        raise click.Abort()

    symbols = store.get_all_symbols(run_id)
    relationships = store.get_all_relationships(run_id)

    result = compute_impact(target_file, relationships, symbols, depth=depth)

    tree = Tree(f"[bold cyan]Impact: {target_file}[/bold cyan] (depth={depth})")
    affected = tree.add(f"[yellow]Affected files ({len(result['affected_files'])})[/yellow]")
    for f in result["affected_files"]:
        affected.add(f)
    tests = tree.add(f"[green]Related tests ({len(result['related_tests'])})[/green]")
    for t in result["related_tests"]:
        tests.add(t)
    syms = tree.add(f"[blue]Affected symbols ({result['total_affected']})[/blue]")
    for s in result["affected_symbols"][:20]:
        syms.add(s)
    if result["total_affected"] > 20:
        syms.add(f"... and {result['total_affected'] - 20} more")
    console.print(tree)
