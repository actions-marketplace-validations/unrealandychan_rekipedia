"""`rekipedia scan` command — full repo analysis."""
from __future__ import annotations

import sys
from pathlib import Path

import click
import yaml
from rich.console import Console

from rekipedia.models.contracts import LLMConfig

console = Console()


def _load_config(repo: Path) -> dict:
    cfg_path = repo / ".rekipedia" / "config.yml"
    if cfg_path.exists():
        return yaml.safe_load(cfg_path.read_text()) or {}
    return {}


def _run_with_refactor(repo: Path, output_dir: Path, verbose: bool) -> None:
    """Run static analysis and write REFACTOR.md after a scan."""
    try:
        from rekipedia.cli.refactor import _build_static_report, _static_walk
        findings = _static_walk(repo)
        report = _build_static_report(repo, findings)
        out_path = output_dir / "REFACTOR.md"
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        console.print(f"  REFACTOR.md : {out_path}")
    except Exception as exc:
        if verbose:
            console.print_exception(show_locals=True)
        else:
            console.print(f"[yellow]  --with-refactor failed: {exc}[/yellow]")


@click.command("scan")
@click.argument(
    "repo",
    default=".",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option("--model", default=None, envvar="REKIPEDIA_MODEL", help="LLM model override.")
@click.option("--no-docker", is_flag=True, default=False, help="Skip Docker, run extractors in-process.")
@click.option("--output-dir", default=None, type=click.Path(path_type=Path), help="Output directory (default: REPO/.rekipedia).")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Enable debug logging (litellm, HTTP, full tracebacks).")
@click.option("--embed-model", default=None, envvar="REKIPEDIA_EMBED_MODEL", help="Embedding model for RAG index (e.g. text-embedding-3-small). If set, auto-embeds after scan.")
@click.option("--embed-provider", default=None, envvar="REKIPEDIA_EMBED_PROVIDER", help="Embedding provider prefix (e.g. openai, ollama, azure). Combined with --embed-model as 'provider/model'.")
@click.option("--languages", "-l", default=None, help="Comma-separated list of languages to include, e.g. python,typescript,go. Default: all.")
@click.option("--force", "-f", is_flag=True, default=False, help="Force re-scan even if a completed scan already exists in the DB.")
@click.option("--with-refactor", is_flag=True, default=False, help="Auto-generate REFACTOR.md after scan completes.")
def scan_cmd(
    repo: Path,
    model: str | None,
    no_docker: bool,
    output_dir: Path | None,
    verbose: bool,
    embed_model: str | None,
    embed_provider: str | None,
    languages: str | None,
    force: bool,
    with_refactor: bool,
) -> None:
    """Scan REPO and (re)build the rekipedia knowledge store.

    Produces wiki pages in OUTPUT_DIR/wiki/, diagrams in OUTPUT_DIR/diagrams/,
    and a JSON manifest in OUTPUT_DIR/exports/manifest.json.

    By default, scan is skipped if a completed scan already exists in the DB.
    Use --force to re-scan regardless.

    \b
    Examples:
        rekipedia scan .
        rekipedia scan ./my-project --no-docker
        rekipedia scan . --verbose
        rekipedia scan . --force          # force re-scan even if DB exists
        rekipedia scan . --with-refactor  # also generate REFACTOR.md
        REKIPEDIA_MODEL=gpt-4o rekipedia scan .
    """
    repo = repo.resolve()
    output_dir = (output_dir or repo / ".rekipedia").resolve()

    # ── Skip if already scanned (unless --force) ──────────────────────────────
    if not force:
        db_path = output_dir / "store.db"
        if db_path.exists():
            try:
                from rekipedia.storage.sqlite_store import SqliteStore  # noqa: PLC0415
                with SqliteStore(db_path) as _store:
                    _existing = _store.get_latest_run_id(str(repo))
                if _existing:
                    console.print(
                        f"[bold yellow]⏭  Scan skipped[/bold yellow] — completed scan already exists "
                        f"([dim]{db_path}[/dim])\n"
                        f"  Use [bold]--force[/bold] / [bold]-f[/bold] to re-scan."
                    )
                    return
            except Exception:
                pass  # DB unreadable — proceed with scan

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
        embed_base_url=llm_cfg_raw.get("embed_base_url") or "",
    )

    console.print(f"[bold green]rekipedia scan[/bold green] {repo}")
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
    # Parse languages filter
    lang_list: list[str] | None = None
    if languages:
        lang_list = [l.strip().lower() for l in languages.split(",") if l.strip()]
        console.print(f"  languages: [cyan]{', '.join(lang_list)}[/cyan]")

    console.rule()

    from rekipedia.orchestrator.run_digest import run_digest  # noqa: PLC0415

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
            languages=lang_list,
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

    # ── Optional: generate REFACTOR.md ────────────────────────────────────────
    if with_refactor:
        console.rule()
        console.print("[bold cyan]rekipedia refactor[/bold cyan] (triggered by --with-refactor)")
        _run_with_refactor(repo, output_dir, verbose)
