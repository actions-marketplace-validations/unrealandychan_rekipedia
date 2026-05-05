---
slug: module-cli
title: "CLI Module Documentation"
section: core-components
tags: [modules, cli]
pin: false
importance: 50
created_at: 2026-05-05T03:44:50Z
rekipedia_version: 0.10.1
---

# CLI Module Documentation

## Overview

The CLI module in the Rekipedia project provides a command-line interface for interacting with various functionalities of the system. This module includes commands for scanning repositories, embedding indexes, exporting data, managing configurations, and more. The CLI module is designed to be user-friendly and supports a wide range of operations that facilitate the management and analysis of code repositories.

The CLI commands are implemented using the `click` library, which provides a simple and intuitive way to create command-line interfaces. Each command is defined as a function and registered with `click` to handle specific tasks.

## Key Functions

### `main()`
The `main()` function is the entry point for the CLI module. It initializes the CLI and registers all the available commands.

```python
def main():
    """rekipedia — agentic repo-to-wiki knowledge store."""
    pass
```
> **Sources:** `src/rekipedia/cli/__init__.py` · L25–L26 · [`main`](src/rekipedia/cli/__init__.py#L25)

### `_print_banner()`
The `_print_banner()` function prints the Rekipedia ASCII art banner using the `pyfiglet` library.

```python
def _print_banner():
    """Print the REKIPEDIA ASCII art banner (two-line ansi_shadow layout)."""
    pass
```
> **Sources:** `src/rekipedia/cli/ask.py` · L24–L34 · [`_print_banner`](src/rekipedia/cli/ask.py#L24)

### `_load_config()`
The `_load_config()` function loads the configuration for the repository from a YAML file.

```python
def _load_config(repo):
    pass
```
> **Sources:** `src/rekipedia/cli/ask.py` · L37–L41 · [`_load_config`](src/rekipedia/cli/ask.py#L37)

### `_build_llm_config()`
The `_build_llm_config()` function builds the configuration for the LLM (Language Learning Model) based on the repository and model specified.

```python
def _build_llm_config(repo, model):
    pass
```
> **Sources:** `src/rekipedia/cli/ask.py` · L44–L52 · [`_build_llm_config`](src/rekipedia/cli/ask.py#L44)

### `_answer_streaming()`
The `_answer_streaming()` function handles a single Q&A turn, displaying a spinner while waiting and then streaming tokens to return the answer text.

```python
def _answer_streaming(question, repo, output_dir, llm_config, history):
    """Run one Q&A turn: spinner while waiting, then stream tokens. Returns answer text."""
    pass
```
> **Sources:** `src/rekipedia/cli/ask.py` · L55–L112 · [`_answer_streaming`](src/rekipedia/cli/ask.py#L55)

### `ask_cmd()`
The `ask_cmd()` function provides an interactive grounded Q&A about the scanned repository. It supports both single-shot mode and REPL loop.

```python
def ask_cmd(question_arg, question, repo, model, output_dir, history_limit, no_save_session, no_rewrite):
    """Interactive grounded Q&A about the scanned repository.

    Optionally pass QUESTION directly as a positional argument for single-shot mode.
    Starts a REPL loop if no question is provided — ask until you press Ctrl+C.
    Answers are streamed in real-time from the LLM.
    Conversation history is kept for multi-turn context (--history-limit turns).

    Examples:
        rekipedia ask                                   # interactive REPL
        rekipedia ask "How does the auth flow work?"    # positional single-shot
        rekipedia ask -q "What are the entry points?"  # flag single-shot
        rekipedia ask --repo ./my-project
        rekipedia ask --history-limit 20
    """
    pass
```
> **Sources:** `src/rekipedia/cli/ask.py` · L129–L231 · [`ask_cmd`](src/rekipedia/cli/ask.py#L129)

### `context_cmd()`
The `context_cmd()` function generates an agent-ready single-file context document.

```python
def context_cmd(repo, output, max_tokens, output_dir):
    """Generate an agent-ready single-file context document.

    Examples:
        rekipedia context
        rekipedia context --repo ./myproject --output ctx.md --max-tokens 16000
    """
    pass
```
> **Sources:** `src/rekipedia/cli/context.py` · L45–L152 · [`context_cmd`](src/rekipedia/cli/context.py#L45)

### `diff_cmd()`
The `diff_cmd()` function compares two graph snapshots, defaulting to the last two snapshots.

```python
def diff_cmd(snapshot_a, snapshot_b, output_dir, out):
    """Compare two graph snapshots (defaults to last two)."""
    pass
```
> **Sources:** `src/rekipedia/cli/diff.py` · L15–L46 · [`diff_cmd`](src/rekipedia/cli/diff.py#L15)

### `embed_cmd()`
The `embed_cmd()` function builds or refreshes the RAG embed index for a specified repository path.

```python
def embed_cmd(repo_path, output_dir, model, provider, api_key, base_url, top_k, verbose):
    """Build or refresh the RAG embed index for REPO_PATH."""
    pass
```
> **Sources:** `src/rekipedia/cli/embed.py` · L85–L179 · [`embed_cmd`](src/rekipedia/cli/embed.py#L85)

### `export_cmd()`
The `export_cmd()` function exports the wiki to a portable file format.

```python
def export_cmd(repo_path, output_dir, fmt, output, title):
    """Export the wiki to a portable file.

    Examples:
        rekipedia export .
        rekipedia export . --format zip -o wiki.zip
        rekipedia export . --format md -o WIKI.md
    """
    pass
```
> **Sources:** `src/rekipedia/cli/export.py` · L50–L164 · [`export_cmd`](src/rekipedia/cli/export.py#L50)

### `hook_cmd()`
The `hook_cmd()` function manages git hooks for automatic wiki rebuilds.

```python
def hook_cmd():
    """Manage git hooks for automatic wiki rebuilds."""
    pass
```
> **Sources:** `src/rekipedia/cli/hook.py` · L31–L32 · [`hook_cmd`](src/rekipedia/cli/hook.py#L31)

### `install()`
The `install()` function installs a post-commit hook that auto-rebuilds the wiki.

```python
def install():
    """Install a post-commit hook that auto-rebuilds the wiki."""
    pass
```
> **Sources:** `src/rekipedia/cli/hook.py` · L36–L49 · [`install`](src/rekipedia/cli/hook.py#L36)

### `uninstall()`
The `uninstall()` function uninstalls the Rekipedia post-commit hook.

```python
def uninstall():
    """Uninstall the rekipedia post-commit hook."""
    pass
```
> **Sources:** `src/rekipedia/cli/hook.py` · L53–L72 · [`uninstall`](src/rekipedia/cli/hook.py#L53)

### `status()`
The `status()` function shows whether the Rekipedia post-commit hook is installed.

```python
def status():
    """Show whether the rekipedia post-commit hook is installed."""
    pass
```
> **Sources:** `src/rekipedia/cli/hook.py` · L76–L97 · [`status`](src/rekipedia/cli/hook.py#L76)

### `impact_cmd()`
The `impact_cmd()` function shows the blast-radius for a changed file.

```python
def impact_cmd(target_file, depth, output_dir):
    """Show blast-radius for a changed file."""
    pass
```
> **Sources:** `src/rekipedia/cli/impact.py` · L14–L47 · [`impact_cmd`](src/rekipedia/cli/impact.py#L14)

### `init_cmd()`
The `init_cmd()` function initializes Rekipedia in the specified repository.

```python
def init_cmd(repo, no_agent_files):
    """Initialise rekipedia in REPO (default: current directory)."""
    pass
```
> **Sources:** `src/rekipedia/cli/init.py` · L143–L145 · [`init_cmd`](src/rekipedia/cli/init.py#L143)

### `mcp_cmd()`
The `mcp_cmd()` function starts the MCP stdio server exposing Rekipedia tools.

```python
def mcp_cmd(output_dir):
    """Start MCP stdio server exposing rekipedia tools."""
    pass
```
> **Sources:** `src/rekipedia/cli/mcp_cmd.py` · L5–L8 · [`mcp_cmd`](src/rekipedia/cli/mcp_cmd.py#L5)

### `refactor_cmd()`
The `refactor_cmd()` function analyzes the repository and produces a REFACTOR.md with prioritized improvement suggestions.

```python
def refactor_cmd(repo, no_llm, to_stdout, severity, output_json, model, output_dir, no_docker, verbose, languages):
    """Analyse REPO and produce a REFACTOR.md with prioritised improvement suggestions.

    Runs a two-phase pipeline:

    1. Static analysis  — scans every source file for TODO/FIXME/HACK/XXX
                          annotations and extraction-level risks.
    2. LLM enrichment   — feeds the extracted symbols and relationships to the
                          LLM to generate a full technical-debt report.

    Pass --no-llm to run phase 1 only (fast, no API key required).

    Examples:
        rekipedia refactor .
        rekipedia refactor . --no-llm
        rekipedia refactor . --stdout | claude --context -
        rekipedia refactor . --severity high
        rekipedia refactor . --json
        REKIPEDIA_MODEL=gpt-4o rekipedia refactor .
    """
    pass
```
> **Sources:** `src/rekipedia/cli/refactor.py` · L282–L370 · [`refactor_cmd`](src/rekipedia/cli/refactor.py#L282)

### `scan_cmd()`
The `scan_cmd()` function scans the repository and rebuilds the Rekipedia knowledge store.

```python
def scan_cmd(repo, model, no_docker, output_dir, verbose, embed_model, embed_provider, languages, force, no_llm, stdout_refactor, with_refactor):
    """Scan REPO and (re)build the rekipedia knowledge store.

    Produces wiki pages in OUTPUT_DIR/wiki/, diagrams in OUTPUT_DIR/diagrams/,
    a JSON manifest in OUTPUT_DIR/exports/manifest.json, and a refactoring
    report in OUTPUT_DIR/REFACTOR.md + OUTPUT_DIR/refactor_report.json.

    By default, scan is skipped if a completed scan already exists in the DB.
    Use --force to re-scan regardless.

    Examples:
        rekipedia scan .
        rekipedia scan ./my-project --no-docker
        rekipedia scan . --verbose
        rekipedia scan . --force          # force re-scan even if DB exists
        rekipedia scan . --no-llm         # static analysis only, skip LLM enrichment
        rekipedia scan . --stdout | claude # pipe refactor guide to Claude
        rekipedia scan . --with-refactor  # also generate REFACTOR.md
        REKIPEDIA_MODEL=gpt-4o rekipedia scan .
    """
    pass
```
> **Sources:** `src/rekipedia/cli/scan.py` · L57–L186 · [`scan_cmd`](src/rekipedia/cli/scan.py#L57)

### `search_cmd()`
The `search_cmd()` function searches symbols in the codebase graph.

```python
def search_cmd(query, output_dir, all_repos, kind):
    """Search symbols in the codebase graph."""
    pass
```
> **Sources:** `src/rekipedia/cli/search.py` · L12–L43 · [`search_cmd`](src/rekipedia/cli/search.py#L12)

### `serve_cmd()`
The `serve_cmd()` function starts the Rekipedia web UI.

```python
def serve_cmd(repo, port, host, output_dir, model, open_browser):
    """Start the rekipedia web UI.

    Examples:
        rekipedia serve
        rekipedia serve --port 8080
        rekipedia serve --repo ./my-project --no-open
    """
    pass
```
> **Sources:** `src/rekipedia/cli/serve.py` · L26–L72 · [`serve_cmd`](src/rekipedia/cli/serve.py#L26)

### `update_cmd()`
The `update_cmd()` function incrementally refreshes the wiki for files changed since the last scan.

```python
def update_cmd(repo, model, no_docker, output_dir, languages):
    """Incrementally refresh the wiki for files changed since the last scan.

    Re-extracts only changed files and re-synthesises all wiki pages.
    Falls back to a full scan if no previous successful scan exists.

    Examples:
        rekipedia update .
        rekipedia update ./my-project --no-docker
        REKIPEDIA_MODEL=gpt-4o rekipedia update .
    """
    pass
```
> **Sources:** `src/rekipedia/cli/update.py` · L35–L101 · [`update_cmd`](src/rekipedia/cli/update.py#L35)

### `watch_cmd()`
The `watch_cmd()` function starts a multi-repo daemon to watch directories and auto-index on change.

```python
def watch_cmd():
    """Multi-repo daemon — watch directories and auto-index on change."""
    pass
```
> **Sources:** `src/rekipedia/cli/watch.py` · L7–L9 · [`watch_cmd`](src/rekipedia/cli/watch.py#L7)

### `watch_add()`
The `watch_add()` function registers a repository to watch.

```python
def watch_add(path):
    """Register a repo to watch."""
    pass
```
> **Sources:** `src/rekipedia/cli/watch.py` · L13–L16 · [`watch_add`](src/rekipedia/cli/watch.py#L13)

### `watch_remove()`
The `watch_remove()` function unregisters a repository.

```python
def watch_remove(path):
    """Unregister a repo."""
    pass
```
> **Sources:** `src/rekipedia/cli/watch.py` · L20–L23 · [`watch_remove`](src/rekipedia/cli/watch.py#L20)

### `watch_list()`
The `watch_list()` function lists registered repositories.

```python
def watch_list():
    """List registered repos."""
    pass
```
> **Sources:** `src/rekipedia/cli/watch.py` · L26–L33 · [`watch_list`](src/rekipedia/cli/watch.py#L26)

### `watch_start()`
The `watch_start()` function starts the file watcher daemon.

```python
def watch_start():
    """Start the file watcher daemon."""
    pass
```
> **Sources:** `src/rekipedia/cli/watch.py` · L36–L39 · [`watch_start`](src/rekipedia/cli/watch.py#L36)

## Usage Examples

### Running a Scan
To scan a repository and build the knowledge store, use the `scan` command:
```bash
rekipedia scan .
```

### Asking a Question
To ask a question about the repository, use the `ask` command:
```bash
rekipedia ask "How does the auth flow work?"
```

### Exporting the Wiki
To export the wiki to a Markdown file, use the `export` command:
```bash
rekipedia export . --format md -o WIKI.md
```

### Managing Git Hooks
To install a post-commit hook that auto-rebuilds the wiki, use the `install` command:
```bash
rekipedia hook install
```

### Incremental Update
To incrementally update the wiki for changed files, use the `update` command:
```bash
rekipedia update .
```

## Configuration Options

### `.rekipedia/config.yml`
The configuration file for Rekipedia is located at `.rekipedia/config.yml`. This file contains various settings that control the behavior of the CLI commands.

Example configuration:
```yaml
refactor:
  god_node_top_pct: 0.05
  high_fan_in: 10
  high_fan_out: 10
  deep_inheritance_depth: 5
```

### Environment Variables
Environment variables can be used to override certain settings in the configuration file.

Example:
```bash
export REKIPEDIA_MODEL=gpt-4o
```

### Command-Line Arguments
Many CLI commands accept arguments that can be used to customize their behavior.

Example:
```bash
rekipedia scan . --verbose --force
```

## Sources

> **Sources:** `src/rekipedia/cli/__init__.py` · L25–L26 · [`main`](src/rekipedia/cli/__init__.py#L25) · `src/rekipedia/cli/ask.py` · L24–L34 · [`_print_banner`](src/rekipedia/cli/ask.py#L24) · `src/rekipedia/cli/ask.py` · L37–L41 · [`_load_config`](src/rekipedia/cli/ask.py#L37) · `src/rekipedia/cli/ask.py` · L44–L52 · [`_build_llm_config`](src/rekipedia/cli/ask.py#L44) · `src/rekipedia/cli/ask.py` · L55–L112 · [`_answer_streaming`](src/rekipedia/cli/ask.py#L55) · `src/rekipedia/cli/ask.py` · L129–L231 · [`ask_cmd`](src/rekipedia/cli/ask.py#L129) · `src/rekipedia/cli/context.py` · L45–L152 · [`context_cmd`](src/rekipedia/cli/context.py#L45) · `src/rekipedia/cli/diff.py` · L15–L46 · [`diff_cmd`](src/rekipedia/cli/diff.py#L15) · `src/rekipedia/cli/embed.py