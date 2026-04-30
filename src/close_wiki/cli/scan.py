"""`close-wiki scan` command — full repo analysis."""
from __future__ import annotations

import sys
from pathlib import Path

import click
import yaml
from rich.console import Console

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
@click.option("--verbose", "-v", is_flag=True, default=False, help="Enable debug logging (litellm, HTTP, full tracebacks).")
@click.option("--embed-model", default=None, envvar="CLOSE_WIKI_EMBED_MODEL", help="Embedding model for RAG index (e.g. text-embedding-3-small). If set, auto-embeds after scan.")
@click.option("--embed-provider", default=None, envvar="CLOSE_WIKI_EMBED_PROVIDER", help="Embedding provider prefix (e.g. openai, ollama, azure). Combined with --embed-model as 'provider/model'.")
def scan_cmd(
    repo: Path,
    model: str | None,
    no_docker: bool,
    output_dir: Path | None,
    verbose: bool,
    embed_model: str | None,
    embed_provider: str | None,
) -> None:
    """Scan REPO and (re)build the close-wiki knowledge store.

    Produces wiki pages in OUTPUT_DIR/wiki/, diagrams in OUTPUT_DIR/diagrams/,
    and a JSON manifest in OUTPUT_DIR/exports/manifest.json.

    \b
    Examples:
        close-wiki scan .
        close-wiki scan ./my-project --no-docker
        close-wiki scan . --verbose
        CLOSE_WIKI_MODEL=gpt-4o close-wiki scan .
    """
    repo = repo.resolve()
    output_dir = (output_dir or repo / ".close-wiki").resolve()

    cfg = _load_config(repo)
    llm_cfg_raw = cfg.get("llm", {})

    llm_config = LLMConfig(
        model=model or llm_cfg_raw.get("model", "ollama/llama4"),
        api_key=llm_cfg_raw.get("api_key", ""),
        base_url=llm_cfg_raw.get("base_url", ""),
        temperature=llm_cfg_raw.get("temperature", 0.2),
        embed_model=embed_model or llm_cfg_raw.get("embed_model", ""),
        embed_provider=embed_provider or llm_cfg_raw.get("embed_provider", ""),
        embed_api_key=llm_cfg_raw.get("embed_api_key") or llm_cfg_raw.get("api_key", ""),
        embed_base_url=llm_cfg_raw.get("embed_base_url") or llm_cfg_raw.get("base_url", ""),
    )

    console.print(f"[bold green]close-wiki scan[/bold green] {repo}")
    console.print(f"  model    : [cyan]{llm_config.model}[/cyan]")
    console.print(f"  output   : [cyan]{output_dir}[/cyan]")
    console.print(f"  runner   : [cyan]{'local (--no-docker)' if no_docker else 'auto'}[/cyan]")
    if llm_config.embed_model:
        _em = f"{llm_config.embed_provider}/{llm_config.embed_model}" if llm_config.embed_provider else llm_config.embed_model
        console.print(f"  embed    : [cyan]{_em}[/cyan]")
        console.print(f"  embed url: [cyan]{llm_config.embed_base_url or '(default: api.openai.com)'}[/cyan]")
        console.print(f"  embed key: [cyan]{'(set)' if llm_config.embed_api_key else '(not set)'}[/cyan]")
    if verbose:
        console.print("  mode     : [yellow]verbose (debug logging ON)[/yellow]")
    console.rule()

    from close_wiki.orchestrator.run_digest import run_digest  # noqa: PLC0415

    # In verbose mode: print each log line directly so tqdm + log interleave cleanly
    # In normal mode: suppress the text progress callback (tqdm bars handle display)
    def _log(msg: str) -> None:
        if verbose:
            console.print(f"  [dim]{msg}[/dim]")

    try:
        run_digest(
            repo_root=repo,
            output_dir=output_dir,
            llm_config=llm_config,
            force_local=no_docker,
            verbose=verbose,
            progress=_log,
        )
    except Exception as exc:
        if verbose:
            import traceback
            console.print_exception(show_locals=True)
        else:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            console.print("[dim]Tip: run with --verbose for full debug output[/dim]")
        sys.exit(1)

    console.rule()
    console.print("[bold green]✓ Scan complete[/bold green]")
    console.print(f"  Wiki pages  : {output_dir / 'wiki'}")
    console.print(f"  Diagrams    : {output_dir / 'diagrams'}")
    console.print(f"  Manifest    : {output_dir / 'exports' / 'manifest.json'}")
    console.print(f"  Database    : {output_dir / 'store.db'}")
