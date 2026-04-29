"""`close-wiki ask` command — grounded Q&A."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.markdown import Markdown

from close_wiki.models.contracts import LLMConfig

console = Console()


def _load_config(repo: Path) -> dict:
    cfg_path = repo / ".close-wiki" / "config.yml"
    if cfg_path.exists():
        return yaml.safe_load(cfg_path.read_text()) or {}
    return {}


@click.command("ask")
@click.argument("question")
@click.option(
    "--repo",
    default=".",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Repository root (default: current directory).",
)
@click.option("--model", default=None, envvar="CLOSE_WIKI_MODEL", help="LLM model override.")
@click.option("--output-dir", default=None, type=click.Path(path_type=Path), help="Output directory (default: REPO/.close-wiki).")
def ask_cmd(question: str, repo: Path, model: str | None, output_dir: Path | None) -> None:
    """Ask a grounded question about the scanned repository.

    Answers are drawn exclusively from the wiki pages and symbol index
    produced by `close-wiki scan` — no hallucinations.

    \b
    Examples:
        close-wiki ask "How does authentication work?"
        close-wiki ask "What are the entry points?" --repo ./my-project
        close-wiki ask "How do I run the tests?" --model gpt-4o
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

    from close_wiki.orchestrator.run_ask import run_ask  # noqa: PLC0415

    console.print(f"[bold green]close-wiki ask[/bold green] — {question}")
    console.print(f"  model  : [cyan]{llm_config.model}[/cyan]")
    console.rule()

    try:
        answer = run_ask(
            question=question,
            repo_root=repo,
            output_dir=output_dir,
            llm_config=llm_config,
        )
    except RuntimeError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        sys.exit(1)
    except Exception as exc:
        console.print(f"[bold red]LLM error:[/bold red] {exc}")
        sys.exit(1)

    console.print(Markdown(answer))

