"""reki diff — compare two graph snapshots."""
from __future__ import annotations
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()

@click.command("diff")
@click.argument("snapshot_a", required=False)
@click.argument("snapshot_b", required=False)
@click.option("--output-dir", default=".", show_default=True, help="Directory containing .rekipedia/snapshots")
@click.option("--out", default=None, help="Write diff summary to this markdown file")
def diff_cmd(snapshot_a, snapshot_b, output_dir, out):
    """Compare two graph snapshots (defaults to last two)."""
    from rekipedia.orchestrator.snapshot import list_snapshots, load_snapshot, diff_snapshots

    snaps = list_snapshots(Path(output_dir))
    if len(snaps) < 2 and not (snapshot_a and snapshot_b):
        console.print("[red]Need at least 2 snapshots. Run reki scan twice first.[/red]")
        raise click.Abort()

    path_a = Path(snapshot_a) if snapshot_a else snaps[-2]
    path_b = Path(snapshot_b) if snapshot_b else snaps[-1]

    console.print(f"Comparing [cyan]{path_a.name}[/cyan] → [cyan]{path_b.name}[/cyan]")

    snap_a = load_snapshot(path_a)
    snap_b = load_snapshot(path_b)
    result = diff_snapshots(snap_a, snap_b)

    s = result["summary"]
    table = Table(title="Graph Diff Summary")
    table.add_column("Metric")
    table.add_column("Count", justify="right")
    for k, v in s.items():
        table.add_row(k.replace("_", " ").title(), str(v))
    console.print(table)

    if out:
        lines = [f"# Graph Diff: {path_a.name} → {path_b.name}\n"]
        for k, v in s.items():
            lines.append(f"- **{k.replace('_', ' ').title()}**: {v}")
        Path(out).write_text("\n".join(lines), encoding="utf-8")
        console.print(f"[green]Diff written to {out}[/green]")
