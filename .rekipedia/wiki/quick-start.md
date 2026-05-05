---
slug: quick-start
title: "Getting Started: First Run Guide"
section: getting-started
tags: [getting-started, overview]
pin: false
importance: 50
created_at: 2026-05-05T04:24:39Z
rekipedia_version: 0.10.2
---

# Getting Started: First Run Guide

This page is a concise, copy-paste-friendly guide for new contributors who want to verify the project works locally with the smallest possible set of steps. It focuses on the common path: install the CLI, run it, scan a small sample repository, and inspect the generated output.

## Install

The repository supports multiple build/install paths, but the fastest first-run path for contributors working from source is to install the Python package in an isolated environment using `uv` or to build the Go CLI for a standalone binary. The analysis data shows both ecosystems are present, but for a first successful command, the Python CLI entry point is the simplest path to use directly from the repo: `src/rekipedia/__main__.py` is the package entry point, and the CLI subcommands live under `src/rekipedia/cli/`, including [`scan`](src/rekipedia/cli/scan.py) and [`serve`](src/rekipedia/cli/serve.py).

If you want the shortest path from a fresh clone:

```bash
uv sync
uv run python -m rekipedia --help
```

If you prefer a buildable standalone binary, the Go CLI is available as [`go/cmd/rekipedia/main.go`](go/cmd/rekipedia/main.go) and can be built with the repository’s Go build command:

```bash
cd go
CGO_ENABLED=0 go build -ldflags "-s -w" -o /tmp/reki ./cmd/rekipedia
```

For day-one verification, the Python route is usually less setup-heavy because it uses the project’s package entrypoint rather than requiring a manual binary install.

> **Sources:** `src/rekipedia/__main__.py` · `src/rekipedia/cli/scan.py` · `src/rekipedia/cli/serve.py` · `go/cmd/rekipedia/main.go` · `uv.lock` · `pyproject.toml` · `go/go.mod`

## Run the CLI

Once dependencies are installed, confirm the CLI is reachable and that the top-level command is available. The root command is implemented in [`src/rekipedia/cli/__init__.py`](src/rekipedia/cli/__init__.py) and the Go equivalent is [`go/cmd/rekipedia/cmd/root.go`](go/cmd/rekipedia/cmd/root.go), which defines the shared command structure for the native CLI.

Common first check:

```bash
uv run python -m rekipedia --help
```

If you built the Go binary instead:

```bash
/tmp/reki --help
```

You should see a command-line interface with subcommands for scanning, serving, searching, and other actions. For a first run, you only need `scan` and, optionally, `serve` for viewing results.

> **Sources:** `src/rekipedia/cli/__init__.py` · `src/rekipedia/__main__.py` · `go/cmd/rekipedia/cmd/root.go` · `go/cmd/rekipedia/main.go`

## Run the scanner on a sample repo

The quickest way to validate the scanner is to run it against one of the bundled fixtures. The repository includes small sample projects under `tests/fixtures/mini-py-repo/` and `tests/fixtures/mini-ts-repo/`. These are ideal because they are tiny, self-contained, and representative enough to exercise the extraction pipeline.

A common first command is:

```bash
uv run python -m rekipedia scan tests/fixtures/mini-py-repo
```

If you want a TypeScript example instead:

```bash
uv run python -m rekipedia scan tests/fixtures/mini-ts-repo
```

At a high level, the scanner uses language-specific extractors such as [`PythonExtractor`](src/rekipedia/extractors/python_extractor.py) and [`TypeScriptExtractor`](src/rekipedia/extractors/typescript_extractor.py), coordinated by the registry in [`Registry`](src/rekipedia/extractors/base.py). The scan produces structured analysis data that can later be exported into pages, JSON, and graph artifacts via components like [`JSONExporter`](src/rekipedia/exporters/json_export.py) and [`MarkdownExporter`](src/rekipedia/exporters/markdown_export.py).

The exact flags may vary, but the first successful scan typically does two things:
1. walks the repository and extracts symbols/relationships
2. writes output into a generated workspace or export directory

> **Sources:** `src/rekipedia/cli/scan.py` · `src/rekipedia/extractors/base.py` · `src/rekipedia/extractors/python_extractor.py` · `src/rekipedia/extractors/typescript_extractor.py` · `src/rekipedia/exporters/json_export.py` · `src/rekipedia/exporters/markdown_export.py` · `tests/fixtures/mini-py-repo/` · `tests/fixtures/mini-ts-repo/`

## Inspect output

After the scan completes, inspect the generated output rather than trying to understand every artifact immediately. The project’s data model centers on [`AnalysisResult`](src/rekipedia/models/contracts.py#L82) and related contracts like [`Symbol`](src/rekipedia/models/contracts.py#L53), [`Relationship`](src/rekipedia/models/contracts.py#L64), and [`WikiPageSpec`](src/rekipedia/models/contracts.py#L119). That means the output usually has a predictable shape even when the underlying repo is small.

At a high level, expect something like this:

```text
output/
  symbols.json
  relationships.json
  manifest.json
  pages/
    index.md
    ...
  diagrams/
    ...
```

Some runs may also create scan metadata and search-related artifacts, depending on the command and configuration. The storage layer persists run data through [`Store`](src/rekipedia/storage/sqlite_store.py) and related operations, while page synthesis is handled by [`PageBuilder`](src/rekipedia/synthesis/page_builder.py) and diagram generation by [`DiagramBuilder`](src/rekipedia/synthesis/diagram_builder.py).

For your first pass, focus on:
- whether the scan completed without errors
- whether symbols and relationships were emitted
- whether markdown pages were generated
- whether the output directory contains a manifest or summary file you can open

If you want to verify the generated markdown manually, open the top-level page in your editor or view it through the local server once you’re ready to take the next step.

> **Sources:** `src/rekipedia/models/contracts.py` · `src/rekipedia/storage/sqlite_store.py` · `src/rekipedia/synthesis/page_builder.py` · `src/rekipedia/synthesis/diagram_builder.py` · `src/rekipedia/exporters/json_export.py` · `src/rekipedia/exporters/markdown_export.py`

## Next step

Once the first scan works, the natural next step is to run the local server and browse the generated pages. That’s outside the scope of this quick-start guide, but the server implementation is available in [`Server`](src/rekipedia/server/app.py) and the CLI surface includes a [`serve`](src/rekipedia/cli/serve.py) command.

> **Sources:** `src/rekipedia/server/app.py` · `src/rekipedia/cli/serve.py`