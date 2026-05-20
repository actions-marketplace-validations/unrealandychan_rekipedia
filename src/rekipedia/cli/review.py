"""`reki review` — LLM-powered PR diff review grounded in the wiki knowledge store.

Usage:
    reki review                        # auto-detect: git diff HEAD (unstaged)
    reki review --staged               # git diff --staged (staged changes)
    reki review --branch main          # diff current branch vs main
    reki review --diff changes.patch   # diff from a file
    git diff HEAD~1 | reki review      # diff from stdin
    reki review --pr 42                # GitHub PR diff (requires GH_TOKEN)
    reki review --no-stream            # wait for full response before printing

The review is grounded in the repository's rekipedia wiki pages and symbol
index so the LLM can reference real architecture, naming conventions, and
known risks rather than generic advice.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterator

import click
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.spinner import Spinner
from rich.text import Text

from rekipedia.models.contracts import LLMConfig

console = Console()

_REVIEW_SYSTEM_PROMPT = """\
You are an expert code reviewer with deep knowledge of the repository.
You are given:
1. A unified diff (git patch format) of the changes being reviewed
2. The repository's wiki knowledge base — architecture docs, module descriptions, known risks

Your task is to produce a concise, actionable PR review structured as:

## Summary
One paragraph describing what the change does and its overall quality.

## Changed Files
For each file changed, a brief note on what changed and any concerns.

## Issues Found
List any bugs, security issues, performance problems, or logic errors.
Rate each as 🔴 Critical / 🟠 Major / 🟡 Minor / 🔵 Nit.
If no issues, say "No issues found."

## Suggestions
Optional improvements (naming, structure, test coverage, docs).

## Verdict
One of: ✅ LGTM | ⚠️ LGTM with comments | ❌ Needs changes

Focus on real issues grounded in the codebase context. Avoid generic boilerplate.
Be specific: reference file paths, function names, and line numbers from the diff.
"""

_DIFF_CHAR_BUDGET = 60_000   # ~15K tokens of diff
_CONTEXT_CHAR_BUDGET = 40_000  # wiki context budget


# ---------------------------------------------------------------------------
# Diff acquisition helpers
# ---------------------------------------------------------------------------

def _get_git_diff(repo: Path, *, staged: bool = False, branch: str | None = None) -> str:
    """Run git diff and return the unified diff string."""
    import subprocess

    if branch:
        cmd = ["git", "diff", branch, "HEAD"]
    elif staged:
        cmd = ["git", "diff", "--staged"]
    else:
        # Diff of working tree vs HEAD (unstaged) — fall back to staged if empty
        cmd = ["git", "diff", "HEAD"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(repo),
            timeout=30,
        )
        diff = result.stdout.strip()
        if not diff and not staged and not branch:
            # Try staged
            result2 = subprocess.run(
                ["git", "diff", "--staged"],
                capture_output=True, text=True, cwd=str(repo), timeout=30,
            )
            diff = result2.stdout.strip()
        return diff
    except Exception as exc:
        raise RuntimeError(f"git diff failed: {exc}") from exc


def _get_github_pr_diff(pr_number: int, repo: Path) -> str:
    """Fetch a GitHub PR diff using the GH_TOKEN env var."""
    import subprocess

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GH_TOKEN or GITHUB_TOKEN env var required to fetch GitHub PR diff."
        )

    # Get remote URL to determine owner/repo
    try:
        remote = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, cwd=str(repo), timeout=10,
        ).stdout.strip()
    except Exception as exc:
        raise RuntimeError(f"Cannot determine GitHub repo from git remote: {exc}") from exc

    # Parse owner/repo from remote URL (https or ssh)
    import re
    m = re.search(r"[:/]([^/]+/[^/]+?)(?:\.git)?$", remote)
    if not m:
        raise RuntimeError(f"Cannot parse owner/repo from remote URL: {remote}")
    owner_repo = m.group(1)

    import urllib.request
    url = f"https://api.github.com/repos/{owner_repo}/pulls/{pr_number}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3.diff",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch PR #{pr_number} diff: {exc}") from exc


def _truncate_diff(diff: str, budget: int = _DIFF_CHAR_BUDGET) -> tuple[str, bool]:
    """Truncate diff to budget characters, preserving whole file hunks where possible."""
    if len(diff) <= budget:
        return diff, False

    # Try to keep whole file sections (split on "diff --git")
    sections = diff.split("\ndiff --git ")
    truncated_parts = [sections[0]]
    used = len(sections[0])

    for section in sections[1:]:
        chunk = "\ndiff --git " + section
        if used + len(chunk) > budget:
            break
        truncated_parts.append(chunk)
        used += len(chunk)

    return "".join(truncated_parts), True


# ---------------------------------------------------------------------------
# Context assembly from knowledge store
# ---------------------------------------------------------------------------

def _build_review_context(output_dir: Path, llm_config: LLMConfig, diff: str) -> str:
    """Assemble wiki context relevant to the changed files."""
    from rekipedia.orchestrator.run_ask import (  # noqa: PLC0415
        _load_wiki_pages,
        _load_symbol_lines,
        _rank_pages_by_query,
        _extract_keywords,
    )

    # Extract filenames from diff for keyword matching
    import re
    changed_files = re.findall(r"^(?:\+\+\+|---) (?:a/|b/)?(.+)$", diff, re.MULTILINE)
    query_hint = " ".join(set(changed_files))

    page_texts = _load_wiki_pages(output_dir)
    symbol_lines = _load_symbol_lines(output_dir)

    ranked = _rank_pages_by_query(page_texts, query_hint)

    context_parts = ["# Repository Knowledge Context\n"]
    used = sum(len(p) for p in context_parts)

    for page in ranked:
        if used + len(page) > _CONTEXT_CHAR_BUDGET:
            context_parts.append("\n*[Additional wiki pages omitted — token budget reached]*\n")
            break
        context_parts.append(page)
        used += len(page)

    if symbol_lines:
        sym_section = "\n## Symbol Index\n\n" + "\n".join(symbol_lines)
        remaining = _CONTEXT_CHAR_BUDGET - used
        if remaining > 500:
            if len(sym_section) > remaining:
                sym_section = sym_section[:remaining] + "\n*[Symbol index truncated]*"
            context_parts.append(sym_section)

    return "\n\n".join(context_parts)


# ---------------------------------------------------------------------------
# Core review orchestrator
# ---------------------------------------------------------------------------

def run_review(
    diff: str,
    repo_root: Path,
    output_dir: Path,
    llm_config: LLMConfig | None = None,
    *,
    stream: bool = True,
) -> str | Iterator[str]:
    """Run an LLM review of a git diff grounded in the knowledge store.

    Args:
        diff: Unified diff string (git patch format).
        repo_root: Repository root path.
        output_dir: `.rekipedia/` directory.
        llm_config: LLM settings.
        stream: If True, returns an Iterator[str] of text chunks.
                If False, returns the full review string.

    Returns:
        str (stream=False) or Iterator[str] (stream=True).

    Raises:
        RuntimeError: If the diff is empty.
    """
    from rekipedia.llm.client import LLMClient  # noqa: PLC0415

    llm_config = llm_config or LLMConfig()

    if not diff.strip():
        raise RuntimeError("Diff is empty — nothing to review.")

    truncated_diff, was_truncated = _truncate_diff(diff)

    # Try to load wiki context if the knowledge store exists
    context = ""
    db_path = output_dir / "store.db"
    if db_path.exists():
        try:
            context = _build_review_context(output_dir, llm_config, truncated_diff)
        except Exception:
            context = ""  # context is optional

    truncation_note = (
        "\n\n> ⚠️ **Note:** The diff was truncated to fit the context window. "
        "Only the first files are shown.\n"
        if was_truncated
        else ""
    )

    prompt = (
        f"Please review the following git diff:\n\n"
        f"```diff\n{truncated_diff}\n```"
        f"{truncation_note}"
    )

    system = _REVIEW_SYSTEM_PROMPT
    if context:
        system = f"{_REVIEW_SYSTEM_PROMPT}\n\n{context}"

    client = LLMClient(llm_config)

    if stream:
        return client.stream(prompt, system=system)
    return client.call(prompt, system=system)


# ---------------------------------------------------------------------------
# CLI command
# ---------------------------------------------------------------------------

@click.command("review")
@click.option(
    "--repo",
    default=".",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Repository root (default: current directory).",
)
@click.option("--model", default=None, envvar="REKIPEDIA_MODEL", help="LLM model override.")
@click.option("--output-dir", default=None, type=click.Path(path_type=Path), help="Output directory.")
@click.option("--diff", "diff_file", default=None, type=click.Path(path_type=Path), help="Path to a unified diff file.")
@click.option("--staged", is_flag=True, default=False, help="Review staged changes (git diff --staged).")
@click.option("--branch", default=None, help="Diff current HEAD vs this branch (e.g. main).")
@click.option("--pr", default=None, type=int, help="GitHub PR number to fetch and review (requires GH_TOKEN).")
@click.option(
    "--no-stream",
    is_flag=True,
    default=False,
    envvar="REKIPEDIA_STREAM",
    help="Disable streaming — wait for the full review before printing.",
)
@click.option("--out", default=None, type=click.Path(path_type=Path), help="Save review to a markdown file.")
def review_cmd(
    repo: Path,
    model: str | None,
    output_dir: Path | None,
    diff_file: Path | None,
    staged: bool,
    branch: str | None,
    pr: int | None,
    no_stream: bool,
    out: Path | None,
) -> None:
    """LLM-powered PR diff review grounded in the repo knowledge store.

    Reads a git diff and produces a structured code review with summary,
    per-file analysis, issues (rated by severity), suggestions, and a verdict.
    The review is grounded in the repository's wiki pages and symbol index.

    \\b
    Examples:
        reki review                          # review git diff HEAD (auto-detect)
        reki review --staged                 # review staged changes
        reki review --branch main            # diff current branch vs main
        reki review --diff changes.patch     # review from a diff file
        git diff HEAD~1 | reki review        # pipe diff from stdin
        reki review --pr 42                  # GitHub PR (requires GH_TOKEN)
        reki review --no-stream              # disable streaming output
        reki review --out review.md          # save review to a file
    """
    import datetime  # noqa: PLC0415

    repo = repo.resolve()
    output_dir = (output_dir or repo / ".rekipedia").resolve()

    llm_cfg_raw: dict = {}
    from rekipedia.config.loader import load_config  # noqa: PLC0415
    cfg = load_config(repo)
    llm_cfg_raw = cfg.get("llm", {})

    llm_config = LLMConfig(
        model=os.environ.get("REKIPEDIA_MODEL") or model or llm_cfg_raw.get("model", "ollama/llama4"),
        api_key=os.environ.get("REKIPEDIA_API_KEY") or llm_cfg_raw.get("api_key", ""),
        base_url=os.environ.get("REKIPEDIA_BASE_URL") or llm_cfg_raw.get("base_url", ""),
        temperature=llm_cfg_raw.get("temperature", 0.2),
    )

    use_stream = not no_stream and os.environ.get("REKIPEDIA_STREAM", "1") != "0"

    # ── Acquire diff ──────────────────────────────────────────────────────────
    diff: str = ""

    if diff_file:
        try:
            diff = Path(diff_file).read_text(encoding="utf-8")
        except Exception as exc:
            console.print(f"[bold red]Error reading diff file:[/bold red] {exc}")
            raise SystemExit(1) from exc

    elif pr is not None:
        with console.status(f"[dim]Fetching GitHub PR #{pr}…[/dim]"):
            try:
                diff = _get_github_pr_diff(pr, repo)
            except RuntimeError as exc:
                console.print(f"[bold red]Error:[/bold red] {exc}")
                raise SystemExit(1) from exc

    elif not sys.stdin.isatty():
        # Pipe mode — read from stdin
        diff = sys.stdin.read()

    else:
        # Auto-detect from git
        with console.status("[dim]Running git diff…[/dim]"):
            try:
                diff = _get_git_diff(repo, staged=staged, branch=branch)
            except RuntimeError as exc:
                console.print(f"[bold red]Error:[/bold red] {exc}")
                raise SystemExit(1) from exc

    if not diff.strip():
        console.print("[yellow]No changes to review.[/yellow]")
        return

    # ── Banner ────────────────────────────────────────────────────────────────
    kb_note = (
        "[dim]grounded in wiki knowledge store[/dim]"
        if (output_dir / "store.db").exists()
        else "[dim]no knowledge store — ungrounded review[/dim]"
    )
    source_note = (
        f"PR #{pr}" if pr is not None
        else f"--branch {branch}" if branch
        else "staged" if staged
        else str(diff_file) if diff_file
        else "stdin" if not sys.stdin.isatty()
        else "git diff HEAD"
    )
    lines_changed = diff.count("\n")
    console.print(
        Panel(
            f"[bold]Source[/bold]  [cyan]{source_note}[/cyan]\n"
            f"[bold]Model[/bold]   [cyan]{llm_config.model}[/cyan]\n"
            f"[bold]Diff[/bold]    [cyan]{lines_changed:,} lines[/cyan]  "
            f"[bold]Output[/bold] {'[dim]streaming[/dim]' if use_stream else '[dim]buffered[/dim]'}\n"
            f"{kb_note}",
            title=" reki review ",
            border_style="cyan",
        )
    )

    # ── Run review ────────────────────────────────────────────────────────────
    console.print(Rule("[bold bright_green]◆ Review[/bold bright_green]", style="bright_green"))

    full_review: str = ""

    if use_stream:
        try:
            chunks_iter = run_review(diff, repo, output_dir, llm_config, stream=True)
        except RuntimeError as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            raise SystemExit(1) from exc

        # Spinner until first chunk
        spinner_text = Spinner("dots", text=Text(" Analysing diff…", style="dim"))
        with Live(spinner_text, console=console, refresh_per_second=12, transient=True):
            try:
                first_chunk = next(chunks_iter)  # type: ignore[arg-type]
            except StopIteration:
                first_chunk = ""
            except Exception as exc:
                console.print(f"[bold red]LLM error:[/bold red] {exc}")
                raise SystemExit(1) from exc

        parts = [first_chunk]
        try:
            with Live(Markdown(first_chunk), console=console, refresh_per_second=15) as live:
                for chunk in chunks_iter:  # type: ignore[union-attr]
                    parts.append(chunk)
                    live.update(Markdown("".join(parts)))
        except Exception as exc:
            console.print(f"\n[bold red]Stream error:[/bold red] {exc}")

        full_review = "".join(parts)

    else:
        spinner_text = Spinner("dots", text=Text(" Analysing diff…", style="dim"))
        with Live(spinner_text, console=console, refresh_per_second=12, transient=True):
            try:
                full_review = run_review(diff, repo, output_dir, llm_config, stream=False)  # type: ignore[assignment]
            except RuntimeError as exc:
                console.print(f"[bold red]Error:[/bold red] {exc}")
                raise SystemExit(1) from exc
        console.print(Markdown(full_review))

    console.rule(style="dim")

    # ── Save to file ──────────────────────────────────────────────────────────
    if out and full_review:
        ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        header = f"# rekipedia review — {source_note}\n_Generated: {ts} · Model: {llm_config.model}_\n\n"
        out_path = Path(out)
        out_path.write_text(header + full_review, encoding="utf-8")
        console.print(f"[dim]Review saved → {out_path}[/dim]")
