"""`close-wiki ask` — interactive grounded Q&A REPL."""
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

import click
import pyfiglet
import yaml
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.spinner import Spinner
from rich.text import Text

from close_wiki.models.contracts import LLMConfig

console = Console()


def _print_banner() -> None:
    """Print the CLOSE-WIKI ASCII art banner."""
    try:
        banner_str = pyfiglet.figlet_format("CLOSE-WIKI", font="slant")
    except pyfiglet.FontNotFound:
        banner_str = pyfiglet.figlet_format("CLOSE-WIKI", font="standard")
    banner_text = Text(banner_str, style="bold cyan")
    console.print(banner_text)
    console.print("  🔍  [bold cyan]Codebase Intelligence[/bold cyan]  ·  [dim]powered by LLM[/dim]\n")


def _load_config(repo: Path) -> dict:
    cfg_path = repo / ".close-wiki" / "config.yml"
    if cfg_path.exists():
        return yaml.safe_load(cfg_path.read_text()) or {}
    return {}


def _build_llm_config(repo: Path, model: str | None) -> LLMConfig:
    cfg = _load_config(repo)
    llm_cfg_raw = cfg.get("llm", {})
    return LLMConfig(
        model=os.environ.get("CLOSE_WIKI_MODEL") or model or llm_cfg_raw.get("model", "ollama/llama4"),
        api_key=os.environ.get("CLOSE_WIKI_API_KEY") or llm_cfg_raw.get("api_key", ""),
        base_url=os.environ.get("CLOSE_WIKI_BASE_URL") or llm_cfg_raw.get("base_url", ""),
        temperature=llm_cfg_raw.get("temperature", 0.2),
    )


def _answer_streaming(question: str, repo: Path, output_dir: Path, llm_config: LLMConfig) -> None:
    """Run one Q&A turn: spinner while waiting, then stream tokens."""
    from close_wiki.orchestrator.run_ask import stream_ask  # noqa: PLC0415

    # Print question header
    console.print(Rule(style="dim"))
    console.print(f"[bold bright_yellow]❯[/bold bright_yellow] {question}\n")

    # Phase 1: spinner until first token
    chunks_iter = None

    try:
        chunks_iter = stream_ask(
            question=question,
            repo_root=repo,
            output_dir=output_dir,
            llm_config=llm_config,
        )
    except (RuntimeError, Exception) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        return

    # Show spinner while waiting for first chunk
    spinner_text = Spinner("dots", text=Text(" Searching wiki & reasoning…", style="dim"))
    with Live(spinner_text, console=console, refresh_per_second=12, transient=True):
        try:
            first_chunk = next(chunks_iter)  # type: ignore[arg-type]
        except StopIteration:
            first_chunk = ""
        except Exception as exc:
            console.print(f"[bold red]LLM error:[/bold red] {exc}")
            return

    # Phase 2: stream remaining tokens to stdout
    console.print(Rule("[bold bright_green]◆ Answer[/bold bright_green]", style="bright_green"))
    sys.stdout.write(first_chunk)
    sys.stdout.flush()
    try:
        for chunk in chunks_iter:  # type: ignore[union-attr]
            sys.stdout.write(chunk)
            sys.stdout.flush()
    except Exception as exc:
        console.print(f"\n[bold red]Stream error:[/bold red] {exc}")
    finally:
        sys.stdout.write("\n")
        sys.stdout.flush()

    console.rule(style="dim")


@click.command("ask")
@click.option("--question", "-q", default=None, help="Single question (non-interactive mode).")
@click.option(
    "--repo",
    default=".",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Repository root (default: current directory).",
)
@click.option("--model", default=None, envvar="CLOSE_WIKI_MODEL", help="LLM model override.")
@click.option("--output-dir", default=None, type=click.Path(path_type=Path), help="Output directory.")
def ask_cmd(question: str | None, repo: Path, model: str | None, output_dir: Path | None) -> None:
    """Interactive grounded Q&A about the scanned repository.

    Starts a REPL loop — ask questions until you press Ctrl+C.
    Answers are streamed in real-time from the LLM.

    \b
    Examples:
        close-wiki ask
        close-wiki ask --repo ./my-project
        close-wiki ask -q "What are the entry points?"   # single-shot
    """
    repo = repo.resolve()
    output_dir = (output_dir or repo / ".close-wiki").resolve()
    llm_config = _build_llm_config(repo, model)

    if question:
        # Single-shot mode
        _print_banner()
        _answer_streaming(question, repo, output_dir, llm_config)
        return

    # Interactive REPL
    _print_banner()

    wiki_dir = output_dir / "wiki"
    panel_content = (
        f"[bold]Model[/bold]   [cyan]{llm_config.model}[/cyan]\n"
        f"[bold]Repo[/bold]    [cyan]{repo}[/cyan]\n"
        f"[bold]Wiki[/bold]    [cyan]{wiki_dir}/[/cyan]\n\n"
        "[dim]Ask anything about the codebase. Type 'exit' or Ctrl+C to quit.[/dim]"
    )
    console.print(Panel(panel_content, title=" close-wiki ask ", border_style="cyan"))
    console.print()

    while True:
        try:
            user_input = console.input("\n[bold bright_yellow]❯ [/bold bright_yellow]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]── session ended ──[/dim]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            console.print("\n[dim]── session ended ──[/dim]")
            break

        _answer_streaming(user_input, repo, output_dir, llm_config)
