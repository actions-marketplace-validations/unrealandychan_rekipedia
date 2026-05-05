---
slug: testing
title: "Testing the Repository End to End"
section: development
tags: [testing, development, reference]
pin: false
importance: 74
created_at: 2026-05-05T04:59:05Z
rekipedia_version: 0.10.3
---

# Testing the Repository End to End

This page documents how the repository is tested end to end, based on the observed test layout, representative suites, and canonical commands in the analysis data. It focuses on what is validated, how fixtures are structured, and which suites correspond to major subsystems. It intentionally does **not** repeat installation steps or CI workflow details.

## Test Strategy Overview

The repository uses a layered testing strategy spanning both the Go implementation under `go/` and the Python test suite under `tests/`. The Go side is organized around package-level `*_test.go` files that validate command wiring, analysis algorithms, storage, orchestration, synthesis, server handlers, and utility packages. The Python side exercises the higher-level behavior of the overall toolchain, including CLI-facing flows, extractors, storage integration, graph output, and fixture-driven repository scanning.

A particularly important pattern in the Go tests is that many suites focus on **end-to-end behavior within a subsystem**, rather than only isolated unit logic. For example, [`TestStaticWalkFindsTODO`](go/cmd/rekipedia/cmd/refactor_test.go#L65) validates the static refactor scan against an actual temporary repository shape, while [`TestDetectGodNodes_DetectsHub`](go/internal/analysis/refactor_detector_test.go#L23) checks graph-analysis heuristics against a constructed dependency graph. Similar integration-oriented tests appear in the command layer, storage layer, and server layer.

The current test corpus also shows explicit coverage of failure paths and guardrails: skipping `.git` and `node_modules`, handling missing files, preserving default config values, and ensuring hooks only uninstall what the tool installed. That makes the suite useful not just for correctness but for regression resistance across file-system, CLI, and data-pipeline behavior.

> **Sources:** `go/cmd/rekipedia/cmd/refactor_test.go` · `go/internal/analysis/refactor_detector_test.go` · `tests/` · `go/cmd/rekipedia/cmd/root_test.go` · `go/cmd/rekipedia/cmd/hook_test.go`

## Test Layout

### Go test layout

The Go tests are colocated with the implementation:

| Area | Test file(s) | Representative validations |
|---|---|---|
| Command surface | `go/cmd/rekipedia/cmd/root_test.go`, `go/cmd/rekipedia/cmd/hook_test.go`, `go/cmd/rekipedia/cmd/refactor_test.go`, `go/cmd/rekipedia/cmd/embed_export_update_test.go` | command registration, flags, hooks, scan output, file writes |
| Analysis engine | `go/internal/analysis/refactor_detector_test.go`, `go/internal/analysis/refactor_enricher_test.go`, `go/internal/analysis/refactor_writer_test.go` | god-node detection, circular dependencies, enrichment, markdown/JSON output |
| Graph / heuristics | `go/internal/graph/graph_analysis_test.go`, `go/internal/graph/hub_gap_test.go` | god nodes, hubs, knowledge gaps |
| Config / contract types | `go/internal/config/loader_test.go`, `go/internal/models/contracts_test.go` | defaults and data model invariants |
| LLM client | `go/internal/llm/client_test.go` | request shaping, retries, embeddings, transient error classification |
| Orchestration | `go/internal/orchestrator/orchestrator_test.go` | snapshotting, sharding, language detection, token estimates |
| RAG / scan metadata | `go/internal/rag/rag_test.go` | chunking, vector store lifecycle, scan metadata round-trips |
| Server | `go/internal/server/server_test.go` | API endpoints, HTML rendering, frontmatter stripping |
| Storage | `go/internal/storage/store_test.go` | SQLite lifecycle, migrations, read/write, isolation |
| Synthesis | `go/internal/synthesis/synthesis_test.go` | planning, page building, diagram generation |
| Extractors | `go/internal/extractor/extractor_test.go` | Go, Python, TypeScript, and config file extraction |
| Filesystem helpers | `go/pkg/fsutil/walk_test.go` | repository walking behavior |

### Python test layout

The Python suite lives under `tests/` and is broader and more scenario-oriented. It includes tests such as `tests/test_scan.py`, `tests/test_refactor_cmd.py`, `tests/test_server.py`, `tests/test_sqlite_store.py`, `tests/test_multilang_extractors.py`, and fixture-based coverage for the end-to-end pipeline. The directory also includes targeted checks for coverage boosts, snapshot diffs, wiki frontmatter, and the MCP/server interfaces.

### Fixture layout

The fixture repositories under `tests/fixtures/mini-py-repo/` and `tests/fixtures/mini-ts-repo/` provide small but realistic source trees for multi-language scanning and extraction. These fixtures include:

- language-specific source files like `core.py`, `main.py`, `utils.py`, `src/index.ts`, and `src/greet.ts`
- project metadata such as `pyproject.toml`, `package.json`, and `tsconfig.json`
- repo policy/config files like `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, and `.github/workflows/ci.yml`

Those fixture repositories are especially important for validating that traversal, extraction, and repository-shaping logic work on realistic directory layouts, not just synthetic snippets.

> **Sources:** `go/cmd/rekipedia/cmd/root_test.go` · `go/cmd/rekipedia/cmd/hook_test.go` · `go/cmd/rekipedia/cmd/refactor_test.go` · `go/internal/analysis/refactor_detector_test.go` · `tests/fixtures/mini-py-repo/` · `tests/fixtures/mini-ts-repo/`

## Canonical Test Commands

The analysis data exposes the following canonical commands used for testing. These are the most defensible “known good” commands from the evidence.

| Command | Purpose / context |
|---|---|
| `go test ./... -v -count=1 -timeout 120s` | Full Go test run across all packages |
| `pytest` | Default Python test entrypoint |
| `pytest tests/ -v --timeout=60 \` | Python test invocation observed with explicit verbosity/timeout flags; the trailing backslash indicates the command was captured mid-line |
| `pip install pytest` | Dependency installation command captured in the evidence, not a test command itself |

For day-to-day verification, the most canonical end-to-end checks are the broad Go suite and the Python suite:

```bash
go test ./... -v -count=1 -timeout 120s
pytest
```

> **Sources:** `test_commands` from analysis data · `go/cmd/rekipedia/cmd/refactor_test.go` · `tests/`

## Fixture Strategy

The repository relies on a mix of temporary, synthetic, and on-disk fixtures.

### Temporary filesystem fixtures in Go

Many Go tests build temporary repositories or files using helper functions, then exercise the real implementation against those directories. Representative examples include:

- [`makeTestRepo`](go/cmd/rekipedia/cmd/refactor_test.go#L50) for static scanning tests
- [`makeGitDir`](go/cmd/rekipedia/cmd/hook_test.go#L10) for hook installation/uninstallation tests
- [`openTestStore`](go/internal/storage/store_test.go#L11) for isolated SQLite-backed storage tests
- [`mockLLMServer`](go/internal/llm/client_test.go#L17) and [`mockEmbeddingServer`](go/internal/llm/client_test.go#L45) for HTTP-based LLM behavior
- [`sampleAnalysisResult`](go/internal/synthesis/synthesis_test.go#L41) and [`mockLLMServer`](go/internal/synthesis/synthesis_test.go#L19) for synthesis planning

This strategy keeps tests close to runtime reality while avoiding dependence on the actual user environment.

### Mock servers and protocol fixtures

Protocol-heavy code is tested with local HTTP servers rather than live external services. The LLM client tests use a mock OpenAI-compatible server to validate request construction, streaming, embeddings, and cancellation behavior. Synthesis tests also use a mock server to validate planner behavior both when valid JSON is returned and when the model returns fenced or invalid output.

### On-disk repository fixtures in Python

The Python tests lean heavily on the fixture repositories in `tests/fixtures/`. This is the clearest evidence of an end-to-end strategy: the scanner and extractor tests can run against realistic repo layouts that contain actual language files, build metadata, and governance files.

> **Sources:** `go/cmd/rekipedia/cmd/refactor_test.go` · `go/cmd/rekipedia/cmd/hook_test.go` · `go/internal/storage/store_test.go` · `go/internal/llm/client_test.go` · `go/internal/synthesis/synthesis_test.go` · `tests/fixtures/mini-py-repo/` · `tests/fixtures/mini-ts-repo/`

## What the Major Test Areas Validate

### CLI commands and flag wiring

The CLI tests validate that commands are registered, flags are exposed, and command-specific behaviors work as expected. Representative examples include:

- [`TestRefactorCmdRegistered`](go/cmd/rekipedia/cmd/refactor_test.go#L15)
- [`TestRefactorCmdFlags`](go/cmd/rekipedia/cmd/refactor_test.go#L28)
- [`TestRefactorCmdUseLine`](go/cmd/rekipedia/cmd/refactor_test.go#L40)
- [`TestLoadLLMConfigDefaults`](go/cmd/rekipedia/cmd/root_test.go#L104)

The hook command is tested for install/uninstall status transitions, including negative cases:

- [`TestHookInstall`](go/cmd/rekipedia/cmd/hook_test.go#L20)
- [`TestHookUninstall`](go/cmd/rekipedia/cmd/hook_test.go#L52)
- [`TestHookUninstallNotOurs`](go/cmd/rekipedia/cmd/hook_test.go#L71)
- [`TestHookStatusInstalled`](go/cmd/rekipedia/cmd/hook_test.go#L91)

The refactor command tests are the most end-to-end of the command suite: they validate static scanning, filtering, markdown report generation, file output, and a flag that disables LLM use.

### Analysis engine behavior

The analysis tests validate both detection logic and enrichment logic. In [`go/internal/analysis/refactor_detector_test.go`](go/internal/analysis/refactor_detector_test.go), the suite covers:

- [`TestDetectGodNodes_DetectsHub`](go/internal/analysis/refactor_detector_test.go#L23) for hub detection
- circular dependency detection and deduplication
- dead-code detection across Python and Go semantics
- high fan-in / fan-out thresholds
- deep inheritance detection
- aggregate multi-rule detection via [`TestDetectAll_ReturnsMultipleKinds`](go/internal/analysis/refactor_detector_test.go#L350)

The enrichment tests in [`go/internal/analysis/refactor_enricher_test.go`](go/internal/analysis/refactor_enricher_test.go) check prompt construction, parsing of model output, caller attachment, and fallback behavior when the LLM is unavailable or returns bad output.

The writer tests in [`go/internal/analysis/refactor_writer_test.go`](go/internal/analysis/refactor_writer_test.go) verify prioritization, section rendering, and output file structure.

### Storage and persistence

The storage suite validates SQLite lifecycle operations, migrations, and CRUD-style persistence for runs, symbols, relationships, wiki pages, QA history, manifests, and snapshot data. [`go/internal/storage/store_test.go`](go/internal/storage/store_test.go) is especially important because it proves that the repository can persist and retrieve the analysis artifacts that later stages consume.

### Extraction and scanning

The extractor tests confirm that the repository can read and classify source files from multiple languages and config formats. The tests cover Go, Python, and TypeScript extraction paths, plus config extraction for `package.json`, `pyproject.toml`, `Dockerfile`, `go.mod`, and `Makefile`. This matters for end-to-end coverage because later graph, synthesis, and server layers depend on those extracted symbols and relationships.

### Orchestration and synthesis

Orchestration tests validate snapshotting, sharding, token-estimation heuristics, and language detection. Synthesis tests verify that planning and page generation can handle valid JSON, fenced JSON, invalid JSON fallback, and diagram generation. These tests are key to the “analysis → plan → pages” pipeline.

### Server and UI

Server tests validate the HTTP routes and UI rendering behavior: health endpoint, page listing, wiki page rendering, frontmatter stripping, graph endpoints, ask endpoints, and missing-resource handling. This is where the repository’s generated knowledge becomes a browsable UI and API.

> **Sources:** `go/cmd/rekipedia/cmd/refactor_test.go` · `go/cmd/rekipedia/cmd/root_test.go` · `go/cmd/rekipedia/cmd/hook_test.go` · `go/internal/analysis/refactor_detector_test.go` · `go/internal/analysis/refactor_enricher_test.go` · `go/internal/analysis/refactor_writer_test.go` · `go/internal/storage/store_test.go` · `go/internal/extractor/extractor_test.go` · `go/internal/orchestrator/orchestrator_test.go` · `go/internal/synthesis/synthesis_test.go` · `go/internal/server/server_test.go`

## Subsystem-to-Test Matrix

| Subsystem | Primary test files / suites | Notes |
|---|---|---|
| CLI root and config | `go/cmd/rekipedia/cmd/root_test.go` | version flag, subcommands, LLM config defaults |
| Hook management | `go/cmd/rekipedia/cmd/hook_test.go` | install/uninstall/status, idempotency, safety checks |
| Refactor scanning | `go/cmd/rekipedia/cmd/refactor_test.go` | static walk, filtering, output generation, command registration |
| Refactor detection | `go/internal/analysis/refactor_detector_test.go` | god nodes, circular deps, fan-in/out, inheritance |
| Refactor enrichment | `go/internal/analysis/refactor_enricher_test.go` | LLM prompt/parse/fallback, caller and note attachment |
| Refactor writing | `go/internal/analysis/refactor_writer_test.go` | markdown/JSON outputs, counts, ordering |
| Extraction | `go/internal/extractor/extractor_test.go` | multi-language parsing and registry routing |
| Graph analysis | `go/internal/graph/graph_analysis_test.go`, `go/internal/graph/hub_gap_test.go` | hubs, god nodes, knowledge gaps |
| LLM client | `go/internal/llm/client_test.go` | HTTP contract, retries, embeddings, transient errors |
| Orchestration | `go/internal/orchestrator/orchestrator_test.go` | snapshots, sharding, language filtering |
| RAG | `go/internal/rag/rag_test.go` | chunking, vector search, metadata persistence |
| Storage | `go/internal/storage/store_test.go` | SQLite persistence and isolation |
| Server | `go/internal/server/server_test.go` | route handling, HTML rendering, JSON APIs |
| Synthesis | `go/internal/synthesis/synthesis_test.go` | planning, payload slicing, diagram building |
| Python integration suite | `tests/test_*.py` | end-to-end flows across CLI, scanning, server, storage, and export |

> **Sources:** `go/cmd/rekipedia/cmd/root_test.go` · `go/cmd/rekipedia/cmd/hook_test.go` · `go/cmd/rekipedia/cmd/refactor_test.go` · `go/internal/analysis/refactor_detector_test.go` · `go/internal/analysis/refactor_enricher_test.go` · `go/internal/analysis/refactor_writer_test.go` · `go/internal/extractor/extractor_test.go` · `go/internal/graph/graph_analysis_test.go` · `go/internal/graph/hub_gap_test.go` · `go/internal/llm/client_test.go` · `go/internal/orchestrator/orchestrator_test.go` · `go/internal/rag/rag_test.go` · `go/internal/storage/store_test.go` · `go/internal/server/server_test.go` · `go/internal/synthesis/synthesis_test.go` · `tests/`

## Practical Reading Guide

If you want to understand whether a change is safe end to end, the fastest path is:

1. Start with the command tests in `go/cmd/rekipedia/cmd/`.
2. Follow into analysis and extraction tests for data correctness.
3. Check storage, synthesis, and server suites for persistence and presentation.
4. Run the canonical Go and Python commands to confirm the full toolchain still works.

That progression mirrors the repository’s execution flow: command entrypoint → scanning/extraction → analysis/enrichment → persistence/synthesis → server/UI.

> **Sources:** `go/cmd/rekipedia/main.go` · `go/cmd/rekipedia/cmd/` · `go/internal/analysis/` · `go/internal/extractor/` · `go/internal/storage/` · `go/internal/synthesis/` · `go/internal/server/`