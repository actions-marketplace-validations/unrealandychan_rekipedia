"""`rekipedia ask` — interactive grounded Q&A REPL."""
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

from rekipedia.models.contracts import LLMConfig

console = Console()


def _print_banner() -> None:
    """Print the REKIPEDIA ASCII art banner (two-line ansi_shadow layout)."""
    try:
        line1 = pyfiglet.figlet_format("REKI", font="ansi_shadow").rstrip("\n")
        line2 = pyfiglet.figlet_format("PEDIA", font="ansi_shadow").rstrip("\n")
    except pyfiglet.FontNotFound:
        line1 = pyfiglet.figlet_format("REKI", font="standard").rstrip("\n")
        line2 = pyfiglet.figlet_format("PEDIA", font="standard").rstrip("\n")
    console.print(Text(line1, style="bold cyan"))
    console.print(Text(line2, style="bold bright_cyan"))
    console.print("  📖  [bold cyan]Repository → Wiki[/bold cyan]  ·  [dim]powered by LLM[/dim]\n")


def _load_config(repo: Path) -> dict:
    cfg_path = repo / ".rekipedia" / "config.yml"
    if cfg_path.exists():
        return yaml.safe_load(cfg_path.read_text()) or {}
    return {}


def _build_llm_config(repo: Path, model: str | None) -> LLMConfig:
    cfg = _load_config(repo)
    llm_cfg_raw = cfg.get("llm", {})
    return LLMConfig(
        model=os.environ.get("REKIPEDIA_MODEL") or model or llm_cfg_raw.get("model", "ollama/llama4"),
        api_key=os.environ.get("REKIPEDIA_API_KEY") or llm_cfg_raw.get("api_key", ""),
        base_url=os.environ.get("REKIPEDIA_BASE_URL") or llm_cfg_raw.get("base_url", ""),
        temperature=llm_cfg_raw.get("temperature", 0.2),
    )


def _answer_streaming(
    question: str,
    repo: Path,
    output_dir: Path,
    llm_config: LLMConfig,
    history: list[dict],
) -> str | None:
    """Run one Q&A turn: spinner while waiting, then stream tokens. Returns answer text."""
    from rekipedia.orchestrator.run_ask import stream_ask  # noqa: PLC0415

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
            history=history,
        )
    except (RuntimeError, Exception) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        return None

    # Show spinner while waiting for first chunk
    spinner_text = Spinner("dots", text=Text(" Searching wiki & reasoning…", style="dim"))
    with Live(spinner_text, console=console, refresh_per_second=12, transient=True):
        try:
            first_chunk = next(chunks_iter)  # type: ignore[arg-type]
        except StopIteration:
            first_chunk = ""
        except Exception as exc:
            console.print(f"[bold red]LLM error:[/bold red] {exc}")
            return None

    # Phase 2: stream remaining tokens to stdout
    answer_parts = [first_chunk]
    console.print(Rule("[bold bright_green]◆ Answer[/bold bright_green]", style="bright_green"))
    sys.stdout.write(first_chunk)
    sys.stdout.flush()
    try:
        for chunk in chunks_iter:  # type: ignore[union-attr]
            sys.stdout.write(chunk)
            sys.stdout.flush()
            answer_parts.append(chunk)
    except Exception as exc:
        console.print(f"\n[bold red]Stream error:[/bold red] {exc}")
    finally:
        sys.stdout.write("\n")
        sys.stdout.flush()

    console.rule(style="dim")
    return "".join(answer_parts)


@click.command("ask")
@click.option("--question", "-q", default=None, help="Single question (non-interactive mode).")
@click.option(
    "--repo",
    default=".",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Repository root (default: current directory).",
)
@click.option("--model", default=None, envvar="REKIPEDIA_MODEL", help="LLM model override.")
@click.option("--output-dir", default=None, type=click.Path(path_type=Path), help="Output directory.")
@click.option("--history-limit", default=10, show_default=True, help="Max conversation turns to keep in context.")
@click.option("--no-save-session", is_flag=True, default=False, help="Do not save session history to disk.")
@click.option("--no-rewrite", is_flag=True, default=False, help="Disable silent query rewriting.")
def ask_cmd(
    question: str | None,
    repo: Path,
    model: str | None,
    output_dir: Path | None,
    history_limit: int,
    no_save_session: bool,
    no_rewrite: bool,
) -> None:
    """Interactive grounded Q&A about the scanned repository.

    Starts a REPL loop — ask questions until you press Ctrl+C.
    Answers are streamed in real-time from the LLM.
    Conversation history is kept for multi-turn context (--history-limit turns).

    \b
    Examples:
        rekipedia ask
        rekipedia ask --repo ./my-project
        rekipedia ask -q "What are the entry points?"   # single-shot
        rekipedia ask --history-limit 20
    """
    import datetime, json as _json  # noqa: PLC0415

    repo = repo.resolve()
    output_dir = (output_dir or repo / ".rekipedia").resolve()
    llm_config = _build_llm_config(repo, model)

    if no_rewrite:
        import os
        os.environ["REKIPEDIA_QUERY_REWRITE"] = "0"

    # Conversation history: [{role, content}, ...]
    history: list[dict] = []

    def _append_history(q: str, answer: str) -> None:
        history.append({"role": "user", "content": q})
        history.append({"role": "assistant", "content": answer})
        # Keep only last history_limit * 2 messages (each turn = 2 msgs)
        max_msgs = history_limit * 2
        if len(history) > max_msgs:
            del history[:-max_msgs]

    def _save_session() -> None:
        if no_save_session or not history:
            return
        sessions_dir = output_dir / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
        session_file = sessions_dir / f"{ts}.json"
        session_file.write_text(
            _json.dumps({"turns": history, "model": llm_config.model}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        console.print(f"[dim]Session saved → {session_file}[/dim]")

    if question:
        # Single-shot mode (no session save)
        _print_banner()
        _answer_streaming(question, repo, output_dir, llm_config, history=[])
        return

    # Interactive REPL
    _print_banner()

    wiki_dir = output_dir / "wiki"
    panel_content = (
        f"[bold]Model[/bold]   [cyan]{llm_config.model}[/cyan]\n"
        f"[bold]Repo[/bold]    [cyan]{repo}[/cyan]\n"
        f"[bold]Wiki[/bold]    [cyan]{wiki_dir}/[/cyan]\n"
        f"[bold]History[/bold] [cyan]{history_limit} turns[/cyan]\n\n"
        "[dim]Ask anything about the codebase. Type 'exit' or Ctrl+C to quit.[/dim]"
    )
    console.print(Panel(panel_content, title=" rekipedia ask ", border_style="cyan"))
    console.print()

    turn = 0
    while True:
        turn += 1
        try:
            user_input = console.input(f"\n[bold bright_yellow][{turn}] ❯ [/bold bright_yellow]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]── session ended ──[/dim]")
            _save_session()
            break

        if not user_input:
            turn -= 1
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            console.print("\n[dim]── session ended ──[/dim]")
            _save_session()
            break

        answer = _answer_streaming(user_input, repo, output_dir, llm_config, history=list(history))
        if answer:
            _append_history(user_input, answer)
