"""reki merge — three-way wiki merge for team sync."""
import json
from pathlib import Path

import click
from rich import print as rprint


@click.command("merge")
@click.argument("bundle_a", type=click.Path(exists=True, file_okay=False))
@click.argument("bundle_b", type=click.Path(exists=True, file_okay=False))
@click.option("--base", type=click.Path(exists=True, file_okay=False), default=None, help="Base bundle for three-way merge")
@click.option("--output", "-o", type=click.Path(), default=".rekipedia/wiki", show_default=True, help="Output directory for merged pages")
@click.option("--no-base", is_flag=True, default=False, help="Force two-way merge (any diff = conflict)")
def merge_cmd(bundle_a: str, bundle_b: str, base: str | None, output: str, no_base: bool) -> None:
    """Merge two wiki bundles (A and B) with optional base for three-way merge."""
    from rekipedia.team_sync.merger import WikiMerger

    base_path = None if (no_base or not base) else Path(base)
    merger = WikiMerger(Path(bundle_a), Path(bundle_b), base=base_path)
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    report = merger.merge(out)
    report_dict = report.to_dict()
    report_path = Path(".rekipedia") / "merge_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report_dict, indent=2), encoding="utf-8")

    s = report_dict["summary"]
    rprint(f"[green]Merge complete[/] → {out}")
    rprint(f"  clean: {s['clean']}  conflict: {s['conflict']}  added: {s['added']}  deleted: {s['deleted']}")
    if report.merged_conflict:
        rprint(f"[yellow]Conflicts in:[/] {', '.join(report.merged_conflict)}")
        rprint("  See .rekipedia/merge_report.json for details")
