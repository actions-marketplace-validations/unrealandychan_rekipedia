"""`reki domain` — map codebase to business domain layers (API/Service/Data/UI/Utility)."""
from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.command("domain")
@click.argument("repo", default=".", metavar="REPO")
@click.option("--output", "-o", default=None, help="Write output to a file.")
@click.option(
    "--format", "fmt",
    default="text",
    type=click.Choice(["text", "json"]),
    help="Output format.",
)
def domain_cmd(repo: str, output: str | None, fmt: str) -> None:
    """Map codebase to business domain layers (API/Service/Data/UI/Utility)."""
    from rekipedia.storage.sqlite_store import SqliteStore
    from rekipedia.analysis.domain import classify_domain

    repo_path = Path(repo).resolve()
    db_path = repo_path / ".rekipedia" / "store.db"
    if not db_path.exists():
        alt = repo_path / ".rekipedia" / "rekipedia.db"
        if alt.exists():
            db_path = alt

    if not db_path.exists():
        console.print(f"[red]No rekipedia DB at {db_path}. Run `reki scan` first.[/red]")
        raise click.Abort()

    store = SqliteStore(db_path)
    run_id = store.get_latest_run_id(str(repo_path))
    if not run_id:
        console.print("[red]No successful scan runs found. Run `reki scan` first.[/red]")
        raise click.Abort()

    result = classify_domain(store, run_id, repo_path)

    if fmt == "json":
        out = json.dumps(result, indent=2)
        if output:
            Path(output).write_text(out)
            console.print(f"[green]Written to {output}[/green]")
        else:
            click.echo(out)
        return

    # Text output
    project_name = repo_path.name
    generated_date = result["generated_at"][:10]
    total_files = result["total_files"]
    layers = result["layers"]
    deps = result["dependencies"]

    lines: list[str] = []
    lines.append(f"🏗️   Domain Architecture — {project_name}")
    lines.append(f"Generated {generated_date} | {total_files} files | {len(layers)} layers")
    lines.append("")

    # Dependency index for quick lookup
    dep_map: dict[str, list[tuple[str, int]]] = {}
    for d in deps:
        dep_map.setdefault(d["from"], []).append((d["to"], d["count"]))

    layer_order = ["API", "Service", "Data", "UI", "Utility"]
    shown_layers = [l for l in layer_order if l in layers]

    for layer_name in shown_layers:
        info = layers[layer_name]
        file_count = len(info["files"])
        sym_count = info["symbol_count"]
        lines.append(f"━━━ {layer_name} Layer ({file_count} files, {sym_count} symbols) ━━━━━━━━━━━━━━━━━━━")
        file_names = [Path(f).name for f in info["files"][:5]]
        if len(info["files"]) > 5:
            file_names.append("...")
        lines.append(f"  Files: {', '.join(file_names)}")
        if info["key_symbols"]:
            lines.append(f"  Key symbols: {', '.join(info['key_symbols'])}")
        for to_layer, count in dep_map.get(layer_name, []):
            if layer_name == "Service" and to_layer == "Data":
                lines.append(f"  → reads/writes {to_layer} ({count} times)")
            else:
                lines.append(f"  → calls {to_layer} ({count} times)")
        lines.append("")

    if len(shown_layers) <= 1 and (not shown_layers or shown_layers == ["Utility"]):
        lines.append("(Tip: this repo has no clear layering — most files are utilities)")
        lines.append("")

    if deps:
        lines.append("🔗  Layer Dependencies")
        for d in deps:
            lines.append(f"   {d['from']} → {d['to']} ({d['count']})")

    text_out = "\n".join(lines)

    if output:
        Path(output).write_text(text_out)
        console.print(f"[green]Written to {output}[/green]")
    else:
        click.echo(text_out)
