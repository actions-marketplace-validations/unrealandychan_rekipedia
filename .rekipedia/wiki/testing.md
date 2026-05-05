---
slug: testing
title: "Testing Across Languages and Subsystems"
section: development
tags: [testing, contributing]
pin: false
importance: 50
created_at: 2026-05-05T04:25:54Z
rekipedia_version: 0.10.2
---

# Testing Across Languages and Subsystems

This repository uses a deliberately broad test strategy spanning Python, Go, and a small amount of JavaScript-adjacent tooling. The test suite is not organized around a single “unit test layer”; instead, it validates behavior at the boundaries that matter most for contributors: CLI wiring, cross-language extraction, storage and export, orchestration flows, web/API responses, and refactor-analysis helpers. The result is a mixed suite that checks both low-level invariants and end-to-end workflow shape.

## Test Layout

The test inventory is split across the language implementations and their subsystems:

- **Python tests** live under `tests/` and primarily exercise the Python CLI and analysis stack. These include command behavior, repository fixtures, RAG/embedding logic, server behavior, and extractor coverage.
- **Go tests** live beside implementation code in `go/**` and cover the rewritten Go implementation of the same product surface: command registration, refactor analysis, extraction, orchestration, storage, server routes, and synthesis.
- **Fixture repositories** under `tests/fixtures/` provide small realistic projects for multi-language scanning and extractor validation.

A useful way to read the layout is by subsystem:

| Area | Representative test files | What they verify |
|------|---------------------------|------------------|
| CLI and command wiring | `go/cmd/rekipedia/cmd/root_test.go`, `go/cmd/rekipedia/cmd/refactor_test.go`, `go/cmd/rekipedia/cmd/hook_test.go`, `go/cmd/rekipedia/cmd/embed_export_update_test.go` | Subcommand registration, flags, defaults, and command-specific behavior |
| Refactor analysis | `go/internal/analysis/refactor_detector_test.go`, `go/internal/analysis/refactor_enricher_test.go`, `go/internal/analysis/refactor_writer_test.go` | Detection, enrichment, report generation, and output writing |
| Extractors | `go/internal/extractor/extractor_test.go`, `tests/test_python_extractor.py`, `tests/test_typescript_extractor.py`, `tests/test_multilang_extractors.py` | Language-specific symbol and relationship extraction |
| RAG / embedding | `go/internal/rag/rag_test.go`, `tests/test_rag.py`, `tests/test_embedder.py` | Chunking, vector storage, scan metadata, embedding/search behavior |
| Server/API | `go/internal/server/server_test.go`, `tests/test_server.py`, `tests/test_graph_api.py`, `tests/test_graph_api_edges.py` | HTTP endpoints, rendering, API responses, and graph data |
| Storage | `go/internal/storage/store_test.go`, `tests/test_sqlite_store.py`, `tests/test_qa_history.py` | Persistence lifecycle, manifests, wiki pages, QA history |
| Orchestration / scanning | `go/internal/orchestrator/orchestrator_test.go`, `tests/test_scan.py`, `tests/test_snapshotter.py`, `tests/test_sharding.py` | Snapshotting, sharding, language detection, and scanning progress |

The fixture strategy is especially important for the Python side: `tests/fixtures/mini-py-repo/` and `tests/fixtures/mini-ts-repo/` provide compact example repositories with language-specific files and agent instructions so tests can validate scanning and extraction against realistic structures rather than handcrafted isolated strings.

> **Sources:** `tests/` · `tests/fixtures/mini-py-repo/` · `tests/fixtures/mini-ts-repo/` · `go/cmd/rekipedia/cmd/root_test.go` · `go/cmd/rekipedia/cmd/refactor_test.go` · `go/internal/extractor/extractor_test.go` · `go/internal/server/server_test.go`

## Test Commands

There are two primary test entry points, one for each implementation track, with a few supporting recipes around them.

### Command recipes

| Recipe | Purpose | Notes |
|--------|---------|-------|
| `pytest` | Run the Python test suite | The main Python verification entry point |
| `pytest tests/ -v --timeout=60 \` | Verbose Python run with per-test timeout | The analysis data shows this as a command fragment, suggesting a longer shell recipe in CI or local docs |
| `pip install pytest` | Install the Python test runner | Useful for bootstrapping a fresh environment |
| `go test ./... -v -count=1 -timeout 120s` | Run the full Go test suite | Covers all Go packages, disables caching, and enforces a global timeout |
| `go test ./... -v -count=1 -timeout 120s` | Recommended for cross-subsystem Go verification | Especially relevant after touching CLI, storage, server, or refactor code |

The presence of both `pytest` and `go test ./...` indicates the repository is currently validated in two distinct ecosystems rather than by a single test harness. That matters for contributors: changing the Python CLI or extractor flow should be tested with `pytest`, while the Go rewrite and its internal packages should be exercised with `go test ./...`.

### Typical contributor workflow

A common sanity-check sequence is:

```bash
pip install pytest
pytest
go test ./... -v -count=1 -timeout 120s
```

That sequence is not a formal script from the analysis data, but it reflects the observable split between the Python and Go test surfaces.

> **Sources:** `tests/` · `go/` · `package.json` · `pyproject.toml` · `go/go.mod` · `Makefile`

## Fixture Strategy

The repository’s fixture strategy is intentionally lightweight but high-signal. Instead of relying only on mocks, tests use small on-disk repositories that resemble real projects:

- `tests/fixtures/mini-py-repo/` contains Python source plus repository metadata such as `pyproject.toml`, `.gitignore`, `.github/workflows/ci.yml`, and agent instruction files.
- `tests/fixtures/mini-ts-repo/` contains a TypeScript project with `package.json`, `tsconfig.json`, `src/index.ts`, and `src/greet.ts`.

This setup supports two important testing goals:

1. **Multi-language traversal** — the repository can verify that discovery and extraction work across different ecosystems.
2. **Metadata-aware behavior** — files such as `.github/copilot-instructions.md`, `AGENTS.md`, and `CLAUDE.md` are present in fixtures so tests can confirm how the tool treats real repository guidance files.

Go tests also use temporary directories and small repo scaffolds. For example, command tests create isolated Git directories or fake test repos to validate command behavior without mutating the working tree. Similarly, storage, RAG, and orchestration tests use small temp stores and synthetic manifests to keep assertions deterministic.

A practical pattern across the suite is “build the smallest realistic environment that still exercises the subsystem.” That keeps tests readable while still validating the tool’s behavior on repository-shaped inputs.

> **Sources:** `tests/fixtures/mini-py-repo/AGENTS.md` · `tests/fixtures/mini-py-repo/pyproject.toml` · `tests/fixtures/mini-ts-repo/package.json` · `tests/fixtures/mini-ts-repo/tsconfig.json` · `go/cmd/rekipedia/cmd/refactor_test.go` · `go/cmd/rekipedia/cmd/hook_test.go` · `go/internal/orchestrator/orchestrator_test.go`

## Coverage of CLI Behaviors

CLI behavior is one of the most explicitly tested areas, and the tests focus on user-visible contracts rather than internal algorithms.

### Root command coverage

The root command tests in [`go/cmd/rekipedia/cmd/root_test.go`](go/cmd/rekipedia/cmd/root_test.go) check the top-level user entry point. Notable coverage includes:

- [`TestRootVersionFlag`](go/cmd/rekipedia/cmd/root_test.go#L9) for version flag behavior
- [`TestRootCommandHasSubcommands`](go/cmd/rekipedia/cmd/root_test.go#L19) for subcommand registration
- [`TestSplitLanguages`](go/cmd/rekipedia/cmd/root_test.go#L66) for language parsing behavior
- [`TestLoadLLMConfig`](go/cmd/rekipedia/cmd/root_test.go#L91) and [`TestLoadLLMConfigDefaults`](go/cmd/rekipedia/cmd/root_test.go#L104) for configuration loading defaults

These tests treat the CLI as a contract: the command tree should exist, flags should resolve correctly, and configuration defaults should be stable.

### Refactor command coverage

The refactor command is tested in [`go/cmd/rekipedia/cmd/refactor_test.go`](go/cmd/rekipedia/cmd/refactor_test.go). Representative cases include:

- [`TestRefactorCmdRegistered`](go/cmd/rekipedia/cmd/refactor_test.go#L15)
- [`TestRefactorCmdFlags`](go/cmd/rekipedia/cmd/refactor_test.go#L28)
- [`TestRefactorCmdUseLine`](go/cmd/rekipedia/cmd/refactor_test.go#L40)
- [`TestStaticWalkFindsTODO`](go/cmd/rekipedia/cmd/refactor_test.go#L65)
- [`TestStaticWalkFindsFIXME`](go/cmd/rekipedia/cmd/refactor_test.go#L87)
- [`TestStaticWalkSkipsGitDir`](go/cmd/rekipedia/cmd/refactor_test.go#L106)
- [`TestStaticWalkSkipsNodeModules`](go/cmd/rekipedia/cmd/refactor_test.go#L125)
- [`TestApplyFilterHigh`](go/cmd/rekipedia/cmd/refactor_test.go#L173)
- [`TestBuildStaticReportWithFindings`](go/cmd/rekipedia/cmd/refactor_test.go#L217)
- [`TestRefactorNoLLMWritesFile`](go/cmd/rekipedia/cmd/refactor_test.go#L238)
- [`TestRefactorJSONWritesFile`](go/cmd/rekipedia/cmd/refactor_test.go#L269)

This suite is especially useful for contributors because it shows the intended shape of the user workflow: scan, filter, report, and write outputs.

### Hook behavior coverage

Hook commands have their own focused suite in [`go/cmd/rekipedia/cmd/hook_test.go`](go/cmd/rekipedia/cmd/hook_test.go). The tests cover install/uninstall/status flows:

- [`TestHookInstall`](go/cmd/rekipedia/cmd/hook_test.go#L20)
- [`TestHookUninstall`](go/cmd/rekipedia/cmd/hook_test.go#L52)
- [`TestHookUninstallNotOurs`](go/cmd/rekipedia/cmd/hook_test.go#L71)
- [`TestHookStatusInstalled`](go/cmd/rekipedia/cmd/hook_test.go#L91)
- [`TestHookStatusNotInstalled`](go/cmd/rekipedia/cmd/hook_test.go#L106)

The tests validate the user-facing lifecycle of the hook command rather than its file-writing internals.

### Embed/export/update behavior coverage

A concentrated suite in [`go/cmd/rekipedia/cmd/embed_export_update_test.go`](go/cmd/rekipedia/cmd/embed_export_update_test.go) covers command registration and output behavior for related workflows:

- [`TestEmbedCmdRegistered`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L17)
- [`TestEmbedCmdFlags`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L30)
- [`TestExportCmdRegistered`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L49)
- [`TestExportCmdDefaultFormat`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L71)
- [`TestUpdateCmdRegistered`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L85)
- [`TestExportJSONMarshal`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L117)
- [`TestUpdateManifestFileWrite`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L141)

This suite is particularly representative of how the repo tests CLI behavior across subsystems: commands are checked both as registered subcommands and as behavior-bearing flows that produce outputs users depend on.

### Command-path summary

| CLI area | Representative tests | Intent |
|----------|----------------------|--------|
| Root | [`TestRootCommandHasSubcommands`](go/cmd/rekipedia/cmd/root_test.go#L19), [`TestRootVersionFlag`](go/cmd/rekipedia/cmd/root_test.go#L9) | Ensure the top-level interface is stable |
| Refactor | [`TestStaticWalkFindsTODO`](go/cmd/rekipedia/cmd/refactor_test.go#L65), [`TestRefactorJSONWritesFile`](go/cmd/rekipedia/cmd/refactor_test.go#L269) | Validate scan/filter/report/update flows |
| Hook | [`TestHookInstall`](go/cmd/rekipedia/cmd/hook_test.go#L20), [`TestHookStatusNotInstalled`](go/cmd/rekipedia/cmd/hook_test.go#L106) | Validate hook lifecycle commands |
| Embed/export/update | [`TestEmbedCmdRegistered`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L17), [`TestExportCmdDefaultFormat`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L71), [`TestUpdateManifestFileWrite`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L141) | Validate output-oriented CLI behaviors |

> **Sources:** `go/cmd/rekipedia/cmd/root_test.go` · `go/cmd/rekipedia/cmd/refactor_test.go` · `go/cmd/rekipedia/cmd/hook_test.go` · `go/cmd/rekipedia/cmd/embed_export_update_test.go` · `go/cmd/rekipedia/cmd/root.go` · `go/cmd/rekipedia/cmd/refactor.go` · `go/cmd/rekipedia/cmd/hook.go` · `go/cmd/rekipedia/cmd/embed.go` · `go/cmd/rekipedia/cmd/export.go` · `go/cmd/rekipedia/cmd/update.go`

## Notable Test Files and Suites by Area

The table below highlights representative suites that contributors are most likely to care about when changing a subsystem.

| Area | Notable test file/suite | Why it matters |
|------|--------------------------|----------------|
| Root CLI | [`go/cmd/rekipedia/cmd/root_test.go`](go/cmd/rekipedia/cmd/root_test.go) | Validates the top-level command surface, versioning, and configuration parsing |
| Refactor CLI | [`go/cmd/rekipedia/cmd/refactor_test.go`](go/cmd/rekipedia/cmd/refactor_test.go) | Exercises static walk, filtering, and report generation |
| Hook CLI | [`go/cmd/rekipedia/cmd/hook_test.go`](go/cmd/rekipedia/cmd/hook_test.go) | Covers install/uninstall/status workflows |
| Embed/export/update CLI | [`go/cmd/rekipedia/cmd/embed_export_update_test.go`](go/cmd/rekipedia/cmd/embed_export_update_test.go) | Verifies command registration and output behavior |
| Refactor analysis | [`go/internal/analysis/refactor_detector_test.go`](go/internal/analysis/refactor_detector_test.go) | Checks detection rules and edge cases |
| Refactor enrichment | [`go/internal/analysis/refactor_enricher_test.go`](go/internal/analysis/refactor_enricher_test.go) | Checks enrichment, prompt building, and LLM-failure handling |
| Refactor writing | [`go/internal/analysis/refactor_writer_test.go`](go/internal/analysis/refactor_writer_test.go) | Checks report shaping and output file generation |
| Multi-language extraction | [`go/internal/extractor/extractor_test.go`](go/internal/extractor/extractor_test.go) | Confirms Python, TypeScript, and config extraction |
| Python/TypeScript repo fixtures | [`tests/fixtures/mini-py-repo`](tests/fixtures/mini-py-repo) and [`tests/fixtures/mini-ts-repo`](tests/fixtures/mini-ts-repo) | Provide realistic inputs for cross-language tests |
| Server/API | [`go/internal/server/server_test.go`](go/internal/server/server_test.go) | Ensures routes and API responses are stable |
| Storage | [`go/internal/storage/store_test.go`](go/internal/storage/store_test.go) | Verifies persistence and run isolation |
| RAG/embedding | [`go/internal/rag/rag_test.go`](go/internal/rag/rag_test.go) | Covers chunking, embeddings, search, and scan metadata |

In the Python test tree, representative areas include CLI behavior, graph analysis, refactor flows, and coverage-related tests such as `tests/test_ask.py`, `tests/test_graph_analysis.py`, `tests/test_update.py`, and `tests/test_hook.py`. The analysis data shows a broad suite, but it does not expose line-level symbols for those Python tests, so this page cites them at the file level only.

> **Sources:** `go/cmd/rekipedia/cmd/root_test.go` · `go/cmd/rekipedia/cmd/refactor_test.go` · `go/cmd/rekipedia/cmd/hook_test.go` · `go/cmd/rekipedia/cmd/embed_export_update_test.go` · `go/internal/analysis/refactor_detector_test.go` · `go/internal/analysis/refactor_enricher_test.go` · `go/internal/analysis/refactor_writer_test.go` · `go/internal/extractor/extractor_test.go` · `go/internal/server/server_test.go` · `go/internal/storage/store_test.go` · `go/internal/rag/rag_test.go` · `tests/`

## Contributing Notes

For contributors, the main takeaway is that tests are intentionally subsystem-oriented. If you change command wiring, update the CLI suites first. If you touch extraction or scanning, run the language- and fixture-based tests. If you modify persistence or server behavior, use the storage and API suites to confirm user-visible behavior still matches expectations.

Because the suite spans languages, it is often best to run both ecosystems after substantial changes, even if your edit was local to one implementation.