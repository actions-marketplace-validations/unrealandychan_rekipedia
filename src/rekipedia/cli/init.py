"""`rekipedia init` command — scaffold the .rekipedia/ bundle in a repo."""
from __future__ import annotations

from pathlib import Path

import click
import yaml
from rich.console import Console

console = Console()

_DEFAULT_CONFIG: dict = {
    "version": 1,
    "ignore": [
        ".git",
        "node_modules",
        "__pycache__",
        ".rekipedia",
    ],
    "languages": ["python", "typescript"],
    "llm": {
        "model": "ollama/llama4",
        "api_key": "",
        "base_url": "",
        "temperature": 0.2,
    },
}

_GITIGNORE_ENTRY = ".rekipedia/store.db\n"

_AGENT_CONTENT_TEMPLATE = """\
# rekipedia — AI Codebase Intelligence

This repository uses [rekipedia](https://github.com/unrealandychan/rekipedia) to maintain a structured wiki and answer questions about the codebase.

## Available commands

| Command | What it does |
|---------|-------------|
| `reki scan .` | Full scan — extract symbols, generate wiki pages, build knowledge store |
| `reki update .` | Incremental refresh — only re-processes changed files |
| `reki ask "<question>"` | Ask anything about the codebase — grounded answers with file:line citations |
| `reki serve .` | Start local web UI at http://127.0.0.1:7070 to browse wiki & ask questions |
| `reki embed .` | Build / rebuild the semantic search index (FAISS) for hybrid RAG |
| `reki export .` | Export wiki to a single file (--format md|zip|json) |

## When to use rekipedia

- Before answering questions about the codebase architecture, run `reki ask "<your question>"` to get grounded context
- After making significant changes, run `reki update .` to keep the wiki current
- When asked to understand how a feature works, check the wiki first with `reki ask`
- When onboarding to an unfamiliar part of the codebase, use `reki ask` for guided explanation

## Setup (first time)

```bash
reki scan .          # generates the wiki and knowledge store
reki embed .         # builds semantic search index (optional, for RAG)
```

The knowledge store lives in `.rekipedia/store.db` — portable, local, no cloud required.
"""


def _write_agent_files(repo_path: Path, force: bool = False) -> None:
    """Write agent instruction files for Claude Code, Codex/OpenAI, and GitHub Copilot."""
    files = [
        (repo_path / "CLAUDE.md", "Claude Code"),
        (repo_path / "AGENTS.md", "Codex / OpenAI Agents"),
        (repo_path / ".github" / "copilot-instructions.md", "GitHub Copilot"),
    ]
    for file_path, platform in files:
        if file_path.exists() and not force:
            console.print(
                f"[yellow]⚠[/yellow]  [bold]{file_path}[/bold] already exists — skipping."
            )
        else:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(_AGENT_CONTENT_TEMPLATE, encoding="utf-8")
            console.print(f"[green]✔[/green]  Created [bold]{file_path}[/bold] ({platform})")


def run_init(repo_path: Path, no_agent_files: bool = False) -> None:
    wiki_dir = repo_path / ".rekipedia"
    config_path = wiki_dir / "config.yml"
    gitignore_path = repo_path / ".gitignore"

    # Create .rekipedia/ if missing
    wiki_dir.mkdir(parents=True, exist_ok=True)

    # Write config.yml — idempotent (skip if already present)
    if config_path.exists():
        console.print(
            f"[yellow]⚠[/yellow]  [bold]{config_path}[/bold] already exists — skipping."
        )
    else:
        config_path.write_text(
            yaml.dump(_DEFAULT_CONFIG, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
        console.print(f"[green]✔[/green]  Created [bold]{config_path}[/bold]")

    # Append .gitignore entry — idempotent
    if gitignore_path.exists():
        existing = gitignore_path.read_text(encoding="utf-8")
        if ".rekipedia/store.db" in existing:
            console.print(
                "[yellow]⚠[/yellow]  .gitignore already contains .rekipedia/store.db — skipping."
            )
        else:
            with gitignore_path.open("a", encoding="utf-8") as fh:
                fh.write(_GITIGNORE_ENTRY)
            console.print("[green]✔[/green]  Added .rekipedia/store.db to .gitignore")
    else:
        gitignore_path.write_text(_GITIGNORE_ENTRY, encoding="utf-8")
        console.print("[green]✔[/green]  Created .gitignore with .rekipedia/store.db")

    if not no_agent_files:
        console.print()
        console.print("[bold]Writing agent instruction files…[/bold]")
        _write_agent_files(repo_path)

    console.print()
    console.print("[bold green]rekipedia initialised.[/bold green]")
    console.print(
        f"  Edit [cyan]{config_path}[/cyan] to choose your LLM provider/model, then run:"
    )
    console.print("  [bold]rekipedia scan .[/bold]")


@click.command("init")
@click.argument(
    "repo",
    default=".",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--no-agent-files",
    is_flag=True,
    default=False,
    help="Skip writing CLAUDE.md, AGENTS.md, and .github/copilot-instructions.md.",
)
def init_cmd(repo: Path, no_agent_files: bool) -> None:
    """Initialise rekipedia in REPO (default: current directory)."""
    run_init(repo.resolve(), no_agent_files=no_agent_files)
