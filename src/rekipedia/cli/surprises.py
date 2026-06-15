"""reki surprises — composite surprise coupling detection (architectural smells and layer violations)."""
from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def _render_table(surprises: list[dict], top: int) -> None:
    console.print(f"\n🧠 [bold]Architectural Surprises & Smells[/bold] — top {top}\n")

    tbl = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    tbl.add_column("Rank", justify="right", style="dim", width=5)
    tbl.add_column("From (Symbol)", min_width=20)
    tbl.add_column("To (Symbol)", min_width=20)
    tbl.add_column("From Layer", style="cyan", width=12)
    tbl.add_column("To Layer", style="magenta", width=12)
    tbl.add_column("Surprise Score", justify="right", style="bold red", width=14)
    tbl.add_column("Smells Detected", width=25)

    for rank, item in enumerate(surprises[:top], 1):
        tbl.add_row(
            str(rank),
            _truncate(item["from"], 25),
            _truncate(item["to"], 25),
            item["from_layer"],
            item["to_layer"],
            f"{item['surprise_score']:.2f}",
            ", ".join(item["smells"]),
        )
    console.print(tbl)
    console.print()


def _render_md(surprises: list[dict], top: int) -> str:
    lines = [f"# Architectural Surprises & Smells — top {top}", ""]
    lines += [
        "| Rank | From (Symbol) | To (Symbol) | From Layer | To Layer | Surprise Score | Smells Detected |",
        "|-----:|---------------|-------------|------------|----------|---------------:|-----------------|",
    ]
    for rank, item in enumerate(surprises[:top], 1):
        lines.append(
            f"| {rank} | `{item['from']}` | `{item['to']}` | {item['from_layer']} | {item['to_layer']} "
            f"| {item['surprise_score']:.2f} | {', '.join(item['smells'])} |"
        )
    lines.append("")
    return "\n".join(lines)


@click.command("surprises")
@click.argument("repo", default=".", type=click.Path())
@click.option("--top", default=10, show_default=True, help="Number of surprises to show")
@click.option(
    "--format",
    "fmt",
    default="table",
    show_default=True,
    type=click.Choice(["table", "json", "md"]),
    help="Output format",
)
def surprises_cmd(repo: str, top: int, fmt: str) -> None:
    """Identify architectural surprises: lone couplings and DDD layer violations."""
    from rekipedia.analysis.surprises import detect_surprises
    from rekipedia.storage.sqlite_store import SqliteStore

    repo_path = Path(repo).resolve()
    db_path = repo_path / ".rekipedia" / "store.db"
    if not db_path.exists():
        alt = repo_path / ".rekipedia" / "rekipedia.db"
        if alt.exists():
            db_path = alt
    if not db_path.exists():
        console.print(f"[red]No rekipedia DB at {db_path}. Run `reki scan` first.[/red]")
        raise click.Abort()

    with SqliteStore(db_path) as store:
        run_id = store.get_latest_run_id(str(repo_path))
        if not run_id:
            console.print("[red]No scan runs found.[/red]")
            raise click.Abort()

        symbols = store.get_all_symbols(run_id)
        relationships = store.get_all_relationships(run_id)

    surprises = detect_surprises(relationships, symbols, limit=top)

    if fmt == "json":
        console.print_json(data=surprises)
    elif fmt == "md":
        console.print(_render_md(surprises, top))
    else:
        _render_table(surprises, top)
