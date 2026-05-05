---
slug: repository-structure
title: "Repository Structure Overview"
section: architecture
tags: [repository-structure, overview]
pin: false
importance: 50
created_at: 2026-05-05T04:24:54Z
rekipedia_version: 0.10.2
---

# Repository Structure Overview

## Annotated Repository Tree

```text
.
├── .github/                         # Automation, CI rules, workflow definitions, and release helpers
│   ├── scripts/                     # Maintenance scripts used by release/automation jobs
│   └── workflows/                   # GitHub Actions pipelines for Go, Python, and npm publishing
├── docs/                            # User-facing documentation and planning notes
│   └── plans/                       # Time-boxed implementation plans and roadmap notes
├── go/                              # Go implementation of the CLI and supporting packages
│   ├── cmd/rekipedia/               # Cobra-style command entrypoint and subcommands
│   ├── internal/                   # Core Go packages: analysis, extractor, server, storage, etc.
│   └── pkg/fsutil/                  # Shared Go utility package(s)
├── pipelines/                       # Harness/pipeline YAML definitions for CI and feature gating
├── schemas/                        # JSON schema definitions for structured outputs
├── scripts/                       # Shell automation and local reporting helpers
├── skills/                        # Agent-facing guidance and shared operational instructions
├── src/rekipedia/                  # Python package: CLI, sandbox, analysis, server, storage, synthesis
│   ├── analysis/                   # Python analysis helpers
│   ├── cli/                        # Python CLI modules
│   ├── exporters/                  # Output formatters
│   ├── extractors/                 # Language/file extractors
│   ├── llm/                        # LLM client layer
│   ├── orchestrator/               # Scan/update/ask orchestration
│   ├── prompts/                    # Prompt templates
│   ├── rag/                        # Retrieval-augmented generation helpers
│   ├── sandbox/                    # Sandbox runtime and tasks
│   ├── server/                     # Web server and templates
│   ├── storage/                    # SQLite storage and migrations
│   ├── synthesis/                  # Page/diagram generation
│   └── watcher/                    # File watching support
├── tests/                           # Python test suite and repository fixtures
│   └── fixtures/                    # Miniature sample repositories for integration tests
├── bin/                             # Small runtime shim(s)
└── top-level config and metadata    # Repository-wide tooling, policy, and packaging files
```

The tree above is intentionally “map-like”: it highlights the main directories and the most visible subdirectories without diving into implementation internals. For example, the Go code lives under [`go/`](go/README.md) and the Python package under [`src/rekipedia/`](src/rekipedia/__init__.py), while docs, tests, and automation live in separate top-level areas.

> **Sources:** `README.md` · `go/README.md` · `src/rekipedia/__init__.py` · `docs/PLAN.md` · `tests/test_server.py`

## Path Summary Table

| Path | Purpose | Notable Files |
|------|---------|---------------|
| `.github/` | Repository automation, contribution rules, and release workflows | `.github/workflows/go-ci.yml`, `.github/workflows/python-ci.yml`, `.github/workflows/go-release.yml`, `.github/scripts/update-homebrew-tap.py`, `.github/copilot-instructions.md` |
| `docs/` | Human-readable documentation, planning, and customization guidance | `docs/PLAN.md`, `docs/customizing.md`, `docs/plans/golang-rewrite.md`, `docs/plans/2026-04-29-phase5-serve.md` |
| `go/` | Standalone Go CLI implementation and related packages | `go/cmd/rekipedia/main.go`, `go/internal/orchestrator/run_update.go`, `go/internal/server/server.go`, `go/internal/storage/store.go`, `go/install.sh` |
| `pipelines/` | Pipeline definitions for harness/CI style execution | `pipelines/harness-ci.yaml`, `pipelines/harness-canary.yaml`, `pipelines/harness-feature-flag-gate.yaml` |
| `schemas/` | JSON schema for structured analysis outputs | `schemas/analysis_result.schema.json` |
| `scripts/` | Shell scripts for local automation and reporting | `scripts/lint-and-report.sh` |
| `skills/` | Agent instructions and shared operational guidance | `skills/shared/rules.md`, `skills/shared/husky-rules.md`, `skills/harness/observability.md`, `skills/harness/testability.md` |
| `src/rekipedia/` | Python package containing the main application logic | `src/rekipedia/__main__.py`, `src/rekipedia/cli/scan.py`, `src/rekipedia/sandbox/runner.py`, `src/rekipedia/server/app.py`, `src/rekipedia/storage/sqlite_store.py`, `src/rekipedia/synthesis/page_builder.py` |
| `tests/` | Python test suite and fixture repositories used for behavior verification | `tests/test_server.py`, `tests/test_python_extractor.py`, `tests/test_sandbox_coverage.py`, `tests/fixtures/mini-py-repo/main.py`, `tests/fixtures/mini-ts-repo/src/index.ts` |
| `bin/` | Small executable shim(s) used by the repo’s tooling | `bin/rekipedia.js` |
| Top-level config and metadata | Root packaging, linting, build, and release configuration | `pyproject.toml`, `package.json`, `go.mod` (in `go/`), `Makefile`, `Dockerfile.sandbox`, `uv.lock`, `CONTRIBUTING.md`, `LICENSE`, `README.md` |

> **Sources:** `package.json` · `pyproject.toml` · `go/go.mod` · `Makefile` · `Dockerfile.sandbox` · `.github/workflows/python-ci.yml` · `.github/workflows/go-ci.yml`

## How the Major Areas Relate

The repository is organized around a split implementation strategy. The Go CLI under [`go/cmd/rekipedia/main.go`](go/cmd/rekipedia/main.go) and its internal packages provide one executable path, while the Python package under [`src/rekipedia/`](src/rekipedia/__init__.py) provides the application’s Python-side modules, including the sandbox entrypoint [`src/rekipedia/sandbox/tasks/analyze_shard.py`](src/rekipedia/sandbox/tasks/analyze_shard.py). Documentation in [`docs/`](docs/PLAN.md) explains product direction and usage, tests in [`tests/`](tests/test_server.py) validate the Python package and fixtures, and automation in [`.github/workflows/`](.github/workflows/go-ci.yml) and [`scripts/`](scripts/lint-and-report.sh) keeps builds, linting, and releases consistent.

In practical terms, the directories complement each other rather than overlap: the Go CLI is the command-line implementation, the Python sandbox is the execution environment for analysis tasks, docs explain the workflow, tests verify the behavior of the Python modules and fixtures, and automation wires the repository together for CI/CD and release publishing.

> **Sources:** `go/cmd/rekipedia/main.go` · `src/rekipedia/sandbox/tasks/analyze_shard.py` · `docs/PLAN.md` · `tests/test_server.py` · `.github/workflows/go-ci.yml` · `.github/workflows/python-ci.yml` · `scripts/lint-and-report.sh`

## Notes on Repository Layout

A few top-level files are worth calling out because they shape the whole repository:

- [`pyproject.toml`](pyproject.toml), [`uv.lock`](uv.lock), and [`package.json`](package.json) indicate that the repo supports both Python and Node-based tooling.
- [`Makefile`](Makefile) provides a conventional entry point for local development tasks.
- [`Dockerfile.sandbox`](Dockerfile.sandbox) defines the sandbox runtime used by the Python-side execution flow.
- [`README.md`](README.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), and [`RELEASE-NOTES.md`](RELEASE-NOTES.md) provide the primary user and contributor entry points.

This layout suggests a repository that is intentionally multi-language, with clear separation between implementation, docs, test fixtures, and automation.

> **Sources:** `pyproject.toml` · `uv.lock` · `package.json` · `Makefile` · `Dockerfile.sandbox` · `README.md` · `CONTRIBUTING.md` · `RELEASE-NOTES.md`