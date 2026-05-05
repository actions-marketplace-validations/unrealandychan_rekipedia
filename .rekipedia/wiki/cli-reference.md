---
slug: cli-reference
title: "CLI Commands Reference"
section: api-reference
tags: [api, cli, reference]
pin: false
importance: 50
created_at: 2026-05-05T03:44:53Z
rekipedia_version: 0.10.1
---

# CLI Commands Reference

This document provides a comprehensive reference for the CLI commands available in the Rekipedia project. It includes sections on the command list, command syntax, options and flags, and examples. Additionally, a table of all CLI flags with their types and default values is provided.

## Command List

Rekipedia offers a variety of CLI commands to interact with the knowledge store, perform scans, manage configurations, and more. Below is a list of the primary commands:

- `rekipedia ask`
- `rekipedia context`
- `rekipedia diff`
- `rekipedia embed`
- `rekipedia export`
- `rekipedia hook`
- `rekipedia impact`
- `rekipedia init`
- `rekipedia mcp`
- `rekipedia refactor`
- `rekipedia scan`
- `rekipedia search`
- `rekipedia serve`
- `rekipedia update`
- `rekipedia watch`

### Sources
> **Sources:** `src/rekipedia/cli/ask.py` · `src/rekipedia/cli/context.py` · `src/rekipedia/cli/diff.py` · `src/rekipedia/cli/embed.py` · `src/rekipedia/cli/export.py` · `src/rekipedia/cli/hook.py` · `src/rekipedia/cli/impact.py` · `src/rekipedia/cli/init.py` · `src/rekipedia/cli/mcp_cmd.py` · `src/rekipedia/cli/refactor.py` · `src/rekipedia/cli/scan.py` · `src/rekipedia/cli/search.py` · `src/rekipedia/cli/serve.py` · `src/rekipedia/cli/update.py` · `src/rekipedia/cli/watch.py`

## Command Syntax

Each command follows a specific syntax pattern. Below are the syntaxes for the primary commands:

### `rekipedia ask`
```
rekipedia ask [OPTIONS] [QUESTION]
```
Options:
- `--repo <path>`: Specify the repository path.
- `--model <model>`: Specify the LLM model to use.
- `--output-dir <path>`: Specify the output directory.
- `--history-limit <number>`: Limit the conversation history.
- `--no-save-session`: Do not save the session.
- `--no-rewrite`: Do not rewrite the question.

### `rekipedia context`
```
rekipedia context [OPTIONS]
```
Options:
- `--repo <path>`: Specify the repository path.
- `--output <file>`: Specify the output file.
- `--max-tokens <number>`: Limit the number of tokens.
- `--output-dir <path>`: Specify the output directory.

### `rekipedia diff`
```
rekipedia diff [OPTIONS]
```
Options:
- `--snapshot-a <file>`: Specify the first snapshot file.
- `--snapshot-b <file>`: Specify the second snapshot file.
- `--output-dir <path>`: Specify the output directory.
- `--out <file>`: Specify the output file.

### `rekipedia embed`
```
rekipedia embed [OPTIONS]
```
Options:
- `--repo-path <path>`: Specify the repository path.
- `--output-dir <path>`: Specify the output directory.
- `--model <model>`: Specify the embedding model.
- `--provider <provider>`: Specify the embedding provider.
- `--api-key <key>`: Specify the API key.
- `--base-url <url>`: Specify the base URL.
- `--top-k <number>`: Specify the number of top results.
- `--verbose`: Enable verbose output.

### `rekipedia export`
```
rekipedia export [OPTIONS]
```
Options:
- `--repo-path <path>`: Specify the repository path.
- `--output-dir <path>`: Specify the output directory.
- `--format <format>`: Specify the export format (e.g., zip, md).
- `--output <file>`: Specify the output file.
- `--title <title>`: Specify the title.

### `rekipedia hook`
```
rekipedia hook [SUBCOMMAND]
```
Subcommands:
- `install`: Install the post-commit hook.
- `uninstall`: Uninstall the post-commit hook.
- `status`: Show the status of the post-commit hook.

### `rekipedia impact`
```
rekipedia impact [OPTIONS]
```
Options:
- `--target-file <file>`: Specify the target file.
- `--depth <number>`: Specify the depth.
- `--output-dir <path>`: Specify the output directory.

### `rekipedia init`
```
rekipedia init [OPTIONS]
```
Options:
- `--repo <path>`: Specify the repository path.
- `--no-agent-files`: Do not create agent instruction files.

### `rekipedia mcp`
```
rekipedia mcp [OPTIONS]
```
Options:
- `--output-dir <path>`: Specify the output directory.

### `rekipedia refactor`
```
rekipedia refactor [OPTIONS]
```
Options:
- `--repo <path>`: Specify the repository path.
- `--no-llm`: Skip LLM enrichment.
- `--to-stdout`: Print output to stdout.
- `--severity <level>`: Specify the severity level.
- `--output-json`: Output JSON format.
- `--model <model>`: Specify the LLM model.
- `--output-dir <path>`: Specify the output directory.
- `--no-docker`: Do not use Docker.
- `--verbose`: Enable verbose output.
- `--languages <list>`: Specify the languages.

### `rekipedia scan`
```
rekipedia scan [OPTIONS]
```
Options:
- `--repo <path>`: Specify the repository path.
- `--model <model>`: Specify the LLM model.
- `--no-docker`: Do not use Docker.
- `--output-dir <path>`: Specify the output directory.
- `--verbose`: Enable verbose output.
- `--embed-model <model>`: Specify the embedding model.
- `--embed-provider <provider>`: Specify the embedding provider.
- `--languages <list>`: Specify the languages.
- `--force`: Force re-scan.
- `--no-llm`: Skip LLM enrichment.
- `--stdout-refactor`: Print refactor guide to stdout.
- `--with-refactor`: Generate REFACTOR.md.

### `rekipedia search`
```
rekipedia search [OPTIONS]
```
Options:
- `--query <query>`: Specify the search query.
- `--output-dir <path>`: Specify the output directory.
- `--all-repos`: Search all repositories.
- `--kind <kind>`: Specify the kind of symbols.

### `rekipedia serve`
```
rekipedia serve [OPTIONS]
```
Options:
- `--repo <path>`: Specify the repository path.
- `--port <number>`: Specify the port.
- `--host <host>`: Specify the host.
- `--output-dir <path>`: Specify the output directory.
- `--model <model>`: Specify the LLM model.
- `--open-browser`: Open the browser.

### `rekipedia update`
```
rekipedia update [OPTIONS]
```
Options:
- `--repo <path>`: Specify the repository path.
- `--model <model>`: Specify the LLM model.
- `--no-docker`: Do not use Docker.
- `--output-dir <path>`: Specify the output directory.
- `--languages <list>`: Specify the languages.

### `rekipedia watch`
```
rekipedia watch [SUBCOMMAND]
```
Subcommands:
- `add <path>`: Register a repository to watch.
- `remove <path>`: Unregister a repository.
- `list`: List registered repositories.
- `start`: Start the file watcher daemon.

### Sources
> **Sources:** `src/rekipedia/cli/ask.py` · `src/rekipedia/cli/context.py` · `src/rekipedia/cli/diff.py` · `src/rekipedia/cli/embed.py` · `src/rekipedia/cli/export.py` · `src/rekipedia/cli/hook.py` · `src/rekipedia/cli/impact.py` · `src/rekipedia/cli/init.py` · `src/rekipedia/cli/mcp_cmd.py` · `src/rekipedia/cli/refactor.py` · `src/rekipedia/cli/scan.py` · `src/rekipedia/cli/search.py` · `src/rekipedia/cli/serve.py` · `src/rekipedia/cli/update.py` · `src/rekipedia/cli/watch.py`

## Options and Flags

Below is a table summarizing the options and flags available for each command, including their types and default values.

| Command       | Option/Flag              | Type    | Default       |
|---------------|--------------------------|---------|---------------|
| `ask`         | `--repo`                 | Path    | Current dir   |
|               | `--model`                | String  | Default model |
|               | `--output-dir`           | Path    | `.rekipedia/` |
|               | `--history-limit`        | Number  | 20            |
|               | `--no-save-session`      | Flag    | False         |
|               | `--no-rewrite`           | Flag    | False         |
| `context`     | `--repo`                 | Path    | Current dir   |
|               | `--output`               | File    | `ctx.md`      |
|               | `--max-tokens`           | Number  | 16000         |
|               | `--output-dir`           | Path    | `.rekipedia/` |
| `diff`        | `--snapshot-a`           | File    | Last snapshot |
|               | `--snapshot-b`           | File    | Last snapshot |
|               | `--output-dir`           | Path    | `.rekipedia/` |
|               | `--out`                  | File    | None          |
| `embed`       | `--repo-path`            | Path    | Current dir   |
|               | `--output-dir`           | Path    | `.rekipedia/` |
|               | `--model`                | String  | Default model |
|               | `--provider`             | String  | Default       |
|               | `--api-key`              | String  | None          |
|               | `--base-url`             | URL     | None          |
|               | `--top-k`                | Number  | 10            |
|               | `--verbose`              | Flag    | False         |
| `export`      | `--repo-path`            | Path    | Current dir   |
|               | `--output-dir`           | Path    | `.rekipedia/` |
|               | `--format`               | String  | `md`          |
|               | `--output`               | File    | `WIKI.md`     |
|               | `--title`                | String  | None          |
| `hook`        | `install`                | Subcommand | None       |
|               | `uninstall`              | Subcommand | None       |
|               | `status`                 | Subcommand | None       |
| `impact`      | `--target-file`          | File    | None          |
|               | `--depth`                | Number  | 3             |
|               | `--output-dir`           | Path    | `.rekipedia/` |
| `init`        | `--repo`                 | Path    | Current dir   |
|               | `--no-agent-files`       | Flag    | False         |
| `mcp`         | `--output-dir`           | Path    | `.rekipedia/` |
| `refactor`    | `--repo`                 | Path    | Current dir   |
|               | `--no-llm`               | Flag    | False         |
|               | `--to-stdout`            | Flag    | False         |
|               | `--severity`             | String  | `medium`      |
|               | `--output-json`          | Flag    | False         |
|               | `--model`                | String  | Default model |
|               | `--output-dir`           | Path    | `.rekipedia/` |
|               | `--no-docker`            | Flag    | False         |
|               | `--verbose`              | Flag    | False         |
|               | `--languages`            | List    | All languages |
| `scan`        | `--repo`                 | Path    | Current dir   |
|               | `--model`                | String  | Default model |
|               | `--no-docker`            | Flag    | False         |
|               | `--output-dir`           | Path    | `.rekipedia/` |
|               | `--verbose`              | Flag    | False         |
|               | `--embed-model`          | String  | Default model |
|               | `--embed-provider`       | String  | Default       |
|               | `--languages`            | List    | All languages |
|               | `--force`                | Flag    | False         |
|               | `--no-llm`               | Flag    | False         |
|               | `--stdout-refactor`      | Flag    | False         |
|               | `--with-refactor`        | Flag    | False         |
| `search`      | `--query`                | String  | None          |
|               | `--output-dir`           | Path    | `.rekipedia/` |
|               | `--all-repos`            | Flag    | False         |
|               | `--kind`                 | String  | None          |
| `serve`       | `--repo`                 | Path    | Current dir   |
|               | `--port`                 | Number  | 8080          |
|               | `--host`                 | String  | `localhost`   |
|               | `--output-dir`           | Path    | `.rekipedia/` |
|               | `--model`                | String  | Default model |
|               | `--open-browser`         | Flag    | False         |
| `update`      | `--repo`                 | Path    | Current dir   |
|               | `--model`                | String  | Default model |
|               | `--no-docker`            | Flag    | False         |
|               | `--output-dir`           | Path    | `.rekipedia/` |
|               | `--languages`            | List    | All languages |
| `watch`       | `add`                    | Subcommand | None       |
|               | `remove`                 | Subcommand | None       |
|               | `list`                   | Subcommand | None       |
|               | `start`                  | Subcommand | None       |

### Sources
> **Sources:** `src/rekipedia/cli/ask.py` · `src/rekipedia/cli/context.py` · `src/rekipedia/cli/diff.py` · `src/rekipedia/cli/embed.py` · `src/rekipedia/cli/export.py` · `src/rekipedia/cli/hook.py` · `src/rekipedia/cli/impact.py` · `src/rekipedia/cli/init.py` · `src/rekipedia/cli/mcp_cmd.py` · `src/rekipedia/cli/refactor.py` · `src/rekipedia/cli/scan.py` · `src/rekipedia/cli/search.py` · `src/rekipedia/cli/serve.py` · `src/rekipedia/cli/update.py` · `src/rekipedia/cli/watch.py`

## Examples

### `rekipedia ask`
To start an interactive REPL for grounded Q&A about the scanned repository:
```bash
rekipedia ask
```

To ask a single-shot question:
```bash
rekipedia ask "How does the auth flow work?"
```

To specify the repository and limit conversation history:
```bash
rekipedia ask --repo ./my-project --history-limit 20
```

### `rekipedia context`
To generate an agent-ready single-file context document:
```bash
rekipedia context --repo ./myproject --output ctx.md --max-tokens 16000
```

### `rekipedia diff`
To compare two graph snapshots:
```bash
rekipedia diff --snapshot-a snapshot1.json --snapshot-b snapshot2.json --output-dir ./diffs
```

### `rekipedia embed`
To build or refresh the RAG embed index for a repository:
```bash
rekipedia embed --repo-path ./my-repo --output-dir ./embeddings --model gpt-3 --provider openai --api-key myapikey --top-k 10 --verbose
```

### `rekipedia export`
To export the wiki to a portable file:
```bash
rekipedia export . --format zip -o wiki.zip
```

### `rekipedia hook`
To install the post-commit hook:
```bash
rekipedia hook install
```

### `rekipedia impact`
To show the blast-radius for a changed file:
```bash
rekipedia impact --target-file src/main.py --depth 3 --output-dir ./impact
```

### `rekipedia init`
To initialize Rekipedia in the current directory:
```bash
rekipedia init
```

### `rekipedia mcp`
To start the MCP stdio server exposing Rekipedia tools:
```bash
rekipedia mcp --output-dir ./mcp
```

### `rekipedia refactor`
To analyze the repository and produce a REFACTOR.md with prioritised improvement suggestions:
```bash
rekipedia refactor . --severity high --output-json --model gpt-4 --output-dir ./refactor
```

### `rekipedia scan`
To scan the repository and rebuild the Rekipedia knowledge store:
```bash
rekipedia scan . --verbose --force --with-refactor
```

### `rekipedia search`
To search symbols in the codebase graph:
```bash
rekipedia search --query "auth flow" --output-dir ./search-results --kind function
```

### `rekipedia serve`
To start the Rekipedia web UI:
```bash
rekipedia serve --repo ./my-project --port 8080 --open-browser
```

### `rekipedia update`
To incrementally refresh the wiki for files