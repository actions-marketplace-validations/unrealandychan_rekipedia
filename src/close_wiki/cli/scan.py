"""`close-wiki scan` command — full repo analysis."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from close_wiki.models.contracts import LLMConfig

console = Console()


def _load_config(repo: Path) -> dict:
    cfg_path = repo / ".close-wiki" / "config.yml"
    if cfg_path.exists():
        return yaml.safe_load(cfg_path.read_text()) or {}
    return {}


@click.command("scan")
@click.argument(
    "repo",
    default=".",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option("--model", default=None, envvar="CLOSE_WIKI_MODEL", help="LLM model override.")
@click.option("--no-docker", is_flag=True, default=False, help="Skip Docker, run extractors in-process.")
@click.option("--output-dir", default=None, type=click.Path(path_type=Path), help="Output directory (default: REPO/.close-wiki).")
def scan_cmd(repo: Path, model: str | None, no_docker: bool, output_dir: Path | None) -> None:
    """Scan REPO and (re)build the close-wiki knowledge store.

    Produces wiki pages in OUTPUT_DIR/wiki/, diagrams in OUTPUT_DIR/diagrams/,
    and a JSON manifest in OUTPUT_DIR/exports/manifest.json.

    \b
    Examples:
        close-wiki scan .
        close-wiki scan ./my-project --no-docker
        CLOSE_WIKI_MODEL=gpt-4o close-wiki scan .
    """
    repo = repo.resolve()
    output_dir = (output_dir or repo / ".close-wiki").resolve()

    cfg = _load_config(repo)
    llm_cfg_raw = cfg.get("llm", {})

    llm_config = LLMConfig(
        model=os.environ.get("CLOSE_WIKI_MODEL") or model or llm_cfg_raw.get("model", "ollama/llama4"),
        api_key=os.environ.get("CLOSE_WIKI_API_KEY") or llm_cfg_raw.get("api_key", ""),
        base_url=os.environ.get("CLOSE_WIKI_BASE_URL") or llm_cfg_raw.get("base_url", ""),
        temperature=llm_cfg_raw.get("temperature", 0.2),
    )

    console.print(f"[bold green]close-wiki scan[/bold green] {repo}")
    console.print(f"  model    : [cyan]{llm_config.model}[/cyan]")
    console.print(f"  output   : [cyan]{output_dir}[/cyan]")
    console.print(f"  runner   : [cyan]{'local (--no-docker)' if no_docker else 'auto'}[/cyan]")

    from close_wiki.orchestrator.run_digest import run_digest  # noqa: PLC0415

    messages: list[str] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Starting…", total=None)

        def _log(msg: str) -> None:
            progress.update(task, description=msg)
            messages.append(msg)

        try:
            run_digest(
                repo_root=repo,
                output_dir=output_dir,
                llm_config=llm_config,
                force_local=no_docker,
                progress=_log,
            )
        except Exception as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            sys.exit(1)

    console.print("[bold green]✓ Scan complete[/bold green]")
    console.print(f"  Wiki pages  : {output_dir / 'wiki'}")
    console.print(f"  Diagrams    : {output_dir / 'diagrams'}")
    console.print(f"  Manifest    : {output_dir / 'exports' / 'manifest.json'}")
    console.print(f"  Database    : {output_dir / 'store.db'}")
