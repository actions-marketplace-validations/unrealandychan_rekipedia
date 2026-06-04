"""`reki domain` — map codebase to business domain layers (API/Service/Data/UI/Utility)."""
from __future__ import annotations

import contextlib
import json
from pathlib import Path

import click
from rich.console import Console
from rich.tree import Tree

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
@click.option("--biz", is_flag=True, default=False, help="Run LLM-driven business domain analysis.")
@click.option("--json", "json_out", is_flag=True, default=False, help="Output business domain graph as JSON (use with --biz).")
def domain_cmd(repo: str, output: str | None, fmt: str, biz: bool, json_out: bool) -> None:  # noqa: C901
    """Map codebase to business domain layers (API/Service/Data/UI/Utility)."""
    if biz:
        _run_biz(repo, output, json_out)
        return

    from rekipedia.analysis.layer_classifier import classify_domain
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
    shown_layers = [lay for lay in layer_order if lay in layers]

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


# ── Business domain sub-command ───────────────────────────────────────────────

_COMPLEXITY_COLOUR = {"simple": "green", "moderate": "yellow", "complex": "red"}


def _run_biz(repo: str, output: str | None, json_out: bool) -> None:
    """Load store, run BizDomainAnalyzer, display results."""
    from rekipedia.analysis.domain_flow_analyzer import BizDomainAnalyzer
    from rekipedia.models.contracts import AnalysisResult
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
        run_id = store.latest_run_id()
        if not run_id:
            console.print("[red]No scan runs found. Run `reki scan` first.[/red]")
            raise click.Abort()

        symbols = store.get_all_symbols(run_id)
        relationships = store.get_all_relationships(run_id)
        entry_points: list[str] = []
        with contextlib.suppress(Exception):
            entry_points = store.get_entry_points(run_id) or []

    analysis_result = AnalysisResult(
        shard_id="biz-domain",
        files_seen=[],
        entry_points=entry_points,
        symbols=symbols,
        relationships=relationships,
    )

    console.print("[dim]Running LLM business domain analysis…[/dim]")
    analyzer = BizDomainAnalyzer()
    graph = analyzer.analyze(analysis_result, project_name=repo_path.name)
    analyzer.save(graph, repo_path)

    if json_out:
        out = graph.model_dump_json(indent=2)
        if output:
            Path(output).write_text(out)
            console.print(f"[green]Written to {output}[/green]")
        else:
            click.echo(out)
        return

    # Rich tree display
    root = Tree("📊 [bold]Business Domain Map[/bold]")
    for domain in graph.domains:
        colour = _COMPLEXITY_COLOUR.get(domain.complexity, "white")
        domain_node = root.add(
            f"🏢 [bold]{domain.name}[/bold]  [[{colour}]{domain.complexity}[/{colour}]]"
        )
        for flow in domain.flows:
            flow_node = domain_node.add(f"🔄 [cyan]{flow.name}[/cyan]")
            for i, step in enumerate(flow.steps, 1):
                loc = f"  [dim]{step.file_path}:{step.line_range[0]}[/dim]" if step.file_path else ""
                flow_node.add(f"{i}. {step.name}{loc}")

    console.print(root)
