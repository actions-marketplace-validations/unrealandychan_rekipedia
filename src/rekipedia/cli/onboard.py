"""reki onboard — generate an onboarding guide for new developers."""
from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.command("onboard")
@click.argument("repo", default=".", metavar="REPO")
@click.option("--output", "-o", default=None, help="Save onboarding guide to file")
@click.option(
    "--format", "fmt",
    default="text",
    type=click.Choice(["text", "md", "json"]),
    help="Output format",
)
def onboard_cmd(repo: str, output: str | None, fmt: str) -> None:
    """Generate an onboarding guide for new developers."""
    from rekipedia.analysis.onboard import build_onboard_guide

    repo_path = Path(repo).resolve()
    db_path = repo_path / ".rekipedia" / "store.db"
    if not db_path.exists():
        alt = repo_path / ".rekipedia" / "rekipedia.db"
        if alt.exists():
            db_path = alt

    if not db_path.exists():
        click.echo(
            f"❌ No scan found at {repo_path / '.rekipedia' / 'store.db'}"
            " — run 'reki scan .' first",
            err=False,
        )
        raise SystemExit(1)

    guide = build_onboard_guide(db_path, repo_path)

    if fmt == "json":
        out_text = json.dumps(guide, indent=2)
    elif fmt == "md":
        out_text = _render_md(guide)
    else:
        out_text = _render_text(guide)

    if output:
        Path(output).write_text(out_text)
        console.print(f"[green]✅ Onboarding guide saved to {output}[/green]")
    else:
        click.echo(out_text)


def _render_text(guide: dict) -> str:
    repo_name = Path(guide["repo"]).name
    date_str = guide["generated_at"][:10]
    counts = guide.get("_counts", {})
    files = counts.get("files", 0)
    symbols = counts.get("symbols", 0)

    lines: list[str] = []
    lines.append(f"🧭  Onboarding Guide — {repo_name}")
    lines.append(f"Generated {date_str} | {files} files | {symbols} symbols\n")

    # Overview
    lines.append("━━━ Overview " + "━" * 39)
    lines.append(f"  {guide['overview']}\n")

    # Getting started
    lines.append("━━━ Getting Started " + "━" * 32)
    for s in guide["getting_started"]:
        title = s["title"].ljust(20)
        lines.append(f"  {s['step']}. {title}{s['cmd']}")
    lines.append("")

    # Architecture
    layers = guide["architecture"]["layers"]
    if layers:
        max_count = max(layers.values()) if layers else 1
        bar_width = 18
        lines.append(f"━━━ Architecture ({len(layers)} layers) " + "━" * 20)
        for layer, cnt in sorted(layers.items(), key=lambda x: -x[1]):
            filled = int(cnt / max_count * bar_width)
            bar = "▓" * filled + "░" * (bar_width - filled)
            label = layer.ljust(8)
            lines.append(f"  {label} {bar}  {cnt:>3} file{'s' if cnt != 1 else ''}")
        lines.append("")

    # Key modules
    if guide["key_modules"]:
        lines.append("━━━ Key Modules (start here) " + "━" * 23)
        for idx, m in enumerate(guide["key_modules"], 1):
            cnt = m.get("count", len(m["symbols"]))
            lines.append(f"  {idx}. {m['path']}   ({cnt} symbols)")
        lines.append("")

    # Symbol patterns
    if guide["patterns"]:
        lines.append("━━━ Symbol Patterns " + "━" * 32)
        parts = [f"{p['kind']}  {p['count']}" for p in guide["patterns"]]
        lines.append("  " + "    ".join(parts))
        lines.append("")

    # Where to go next
    lines.append("━━━ Where to Go Next " + "━" * 30)
    lines.append("  reki tour .                    # guided walkthrough by dependency depth")
    lines.append('  reki ask "<your question>"     # AI-powered Q&A about this codebase')
    lines.append("  reki domain .                  # business domain layer map")
    if guide.get("wiki_dir"):
        lines.append(f"  {guide['wiki_dir']}  # browse generated wiki pages")
    else:
        lines.append("  .rekipedia/wiki/               # browse generated wiki pages")

    return "\n".join(lines)


def _render_md(guide: dict) -> str:
    repo_name = Path(guide["repo"]).name
    date_str = guide["generated_at"][:10]
    counts = guide.get("_counts", {})
    files = counts.get("files", 0)
    symbols = counts.get("symbols", 0)

    lines: list[str] = []
    lines.append(f"# 🧭 Onboarding Guide — {repo_name}")
    lines.append(f"\n*Generated {date_str} | {files} files | {symbols} symbols*\n")

    lines.append("## Overview\n")
    lines.append(guide["overview"] + "\n")

    lines.append("## Getting Started\n")
    for s in guide["getting_started"]:
        lines.append(f"{s['step']}. **{s['title']}** — `{s['cmd']}`")
    lines.append("")

    layers = guide["architecture"]["layers"]
    if layers:
        lines.append(f"## Architecture ({len(layers)} layers)\n")
        for layer, cnt in sorted(layers.items(), key=lambda x: -x[1]):
            lines.append(f"- **{layer}**: {cnt} file{'s' if cnt != 1 else ''}")
        lines.append("")

    if guide["key_modules"]:
        lines.append("## Key Modules (start here)\n")
        for idx, m in enumerate(guide["key_modules"], 1):
            cnt = m.get("count", len(m["symbols"]))
            syms = ", ".join(m["symbols"][:5])
            lines.append(f"{idx}. `{m['path']}` — {cnt} symbols")
            if syms:
                lines.append(f"   - Symbols: `{syms}`")
        lines.append("")

    if guide["patterns"]:
        lines.append("## Symbol Patterns\n")
        for p in guide["patterns"]:
            lines.append(f"- **{p['kind']}**: {p['count']}")
        lines.append("")

    lines.append("## Where to Go Next\n")
    lines.append("```bash")
    lines.append("reki tour .                    # guided walkthrough by dependency depth")
    lines.append('reki ask "<your question>"     # AI-powered Q&A about this codebase')
    lines.append("reki domain .                  # business domain layer map")
    if guide.get("wiki_dir"):
        lines.append(f"# Wiki pages: {guide['wiki_dir']}")
    lines.append("```")

    return "\n".join(lines)
