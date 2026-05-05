---
slug: index
title: "Project Overview"
section: getting-started
tags: [overview, getting-started]
pin: false
importance: 50
created_at: 2026-05-05T03:44:24Z
rekipedia_version: 0.10.1
---

# Project Overview

![Version Badge](https://img.shields.io/badge/version-0.9.7-blue) ![Build Status](https://img.shields.io/github/workflow/status/owner/repo/CI)

## What is it?

Rekipedia is a comprehensive software analysis tool designed to provide insights into codebases by extracting, analyzing, and visualizing code relationships and structures. It supports multiple programming languages and offers a suite of features for developers to understand and improve their code quality and architecture.

## Key Features

- **Multi-language Support**: Analyze codebases written in Python, Go, Java, Rust, and TypeScript.
- **Graph Analysis**: Identify key nodes and relationships within your codebase using advanced graph analysis techniques.
- **Refactoring Tools**: Detect code smells and suggest refactoring opportunities to improve code maintainability.
- **Code Exporters**: Export analysis results in various formats, including JSON and Markdown.
- **CLI Tools**: A set of command-line tools for performing various tasks such as scanning, embedding, and exporting.
- **Web Server**: Host a local server to visualize and interact with the analysis results.
- **Snapshot Management**: Save and compare snapshots of your codebase over time to track changes and impacts.

## Quick Start

To get started with Rekipedia, follow these steps to install and run your first analysis:

```bash
# Clone the repository
git clone https://github.com/yourusername/rekipedia.git
cd rekipedia

# Build the project
CGO_ENABLED=0 go build -ldflags "-s -w" -o /tmp/reki ./cmd/rekipedia

# Run your first analysis
/tmp/reki scan --path /path/to/your/codebase
```

## Repository Map

Here's a high-level view of the repository structure:

```
rekipedia/
├── .github/
│   ├── workflows/
│   └── scripts/
├── go/
│   ├── cmd/
│   ├── internal/
│   ├── pkg/
│   └── Dockerfile
├── src/
│   ├── rekipedia/
│   ├── analysis/
│   ├── cli/
│   ├── exporters/
│   ├── extractors/
│   ├── llm/
│   ├── models/
│   ├── orchestrator/
│   ├── rag/
│   ├── sandbox/
│   ├── server/
│   ├── storage/
│   ├── synthesis/
│   └── watcher/
├── tests/
└── docs/
```

## Architecture at a Glance

Rekipedia's architecture is modular, with each module responsible for a specific aspect of the analysis process. The core modules include the CLI for user interaction, the analysis engine for processing code, and the server for visualizing results. The architecture is designed to be extensible, allowing for easy integration of new languages and features. For a detailed breakdown of the architecture, please refer to the [Architecture Page](architecture.md).

> **Sources:** `src/rekipedia/cli/ask.py` · L129–L231 · [`ask_cmd`](src/rekipedia/cli/ask.py#L129) · `src/rekipedia/analysis/graph_analysis.py` · L11–L34 · [`compute_god_nodes`](src/rekipedia/analysis/graph_analysis.py#L11)