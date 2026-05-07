---
slug: ecosystem-and-integrations
title: "External Integrations, Plugins, and Ecosystem"
section: general
pin: false
importance: 50
created_at: 2026-05-07T04:13:03Z
rekipedia_version: 0.10.9
---

# External Integrations, Plugins, and Ecosystem

## Overview

This page documents the project’s third-party dependencies, external systems, extension surfaces, and adjacent ecosystem context that can be inferred from the repository analysis. The codebase is a multi-language project centered on the Python package [`rekipedia`](src/rekipedia/__init__.py#L1), with a CLI entry point [`main`](src/rekipedia/cli/__init__.py#L26) and a `reki`/`rekipedia` command-line interface exposed in package metadata. The analyzed repository also includes a Go implementation path under `go/`, which uses its own storage layer and CLI commands such as [`Execute`](go/cmd/rekipedia/cmd/root.go#L44) and [`openStore`](go/cmd/rekipedia/cmd/note.go#L101).

The ecosystem surface is primarily shaped by:
- CLI tooling via [`rekipedia.cli.__init__`](src/rekipedia/cli/__init__.py#L1)
- a RAG embedding pipeline in [`rekipedia.rag.embedder`](src/rekipedia/rag/embedder.py#L1)
- a web app factory in [`create_app`](src/rekipedia/server/app.py#L21)
- a persistent store in [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39)
- YAML/Markdown note import via [`import_notes_from_file`](src/rekipedia/notes/__init__.py#L7)

The repository’s relationship statistics show a heavily integrated codebase: **1,996 total relationships**, with **1,757 calls**, **222 imports**, and **17 import edges** recorded in the precomputed analysis.

> **Sources:** `README.md`; `pyproject.toml`; `src/rekipedia/__init__.py` · L1 · [`rekipedia.__init__`](src/rekipedia/__init__.py#L1); `src/rekipedia/cli/__init__.py` · L26–L27 · [`main`](src/rekipedia/cli/__init__.py#L26); `src/rekipedia/rag/embedder.py` · L1–L1 · [`rekipedia.rag.embedder`](src/rekipedia/rag/embedder.py#L1); `src/rekipedia/server/app.py` · L21–L21 · [`create_app`](src/rekipedia/server/app.py#L21); `src/rekipedia/storage/sqlite_store.py` · L39–L39 · [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39)

## External Dependencies

The repository imports a number of third-party libraries across the CLI, server, RAG, and storage layers. The table below lists the significant dependencies evidenced in the analysis.

| Library | Version | Purpose |
|---|---:|---|
| `click` | not pinned in analysis | CLI command parsing and subcommand wiring in [`main`](src/rekipedia/cli/__init__.py#L26), [`embed_cmd`](src/rekipedia/cli/embed.py#L85), and note commands like [`note_add`](src/rekipedia/cli/note.py#L35) |
| `rich` (`rich.console`, `rich.progress`) | not pinned in analysis | Console output and progress UI, notably in [`embed_cmd`](src/rekipedia/cli/embed.py#L85) and [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45) |
| `tqdm` | not pinned in analysis | Embedding progress display in [`embed_cmd`](src/rekipedia/cli/embed.py#L85) |
| `numpy` | not pinned in analysis | Vector math and array storage in [`rekipedia.rag.embedder`](src/rekipedia/rag/embedder.py#L1) |
| `faiss` | not pinned in analysis | Vector index creation/search in [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443) |
| `litellm` | not pinned in analysis | LLM chat and embedding API calls in [`_embed_batch`](src/rekipedia/rag/embedder.py#L416), [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L304), and [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45) |
| `tree_sitter` | not pinned in analysis | AST-aware symbol chunking in [`_symbol_chunk_file_inner`](src/rekipedia/rag/embedder.py#L235) |
| `tree_sitter_python` | not pinned in analysis | Python grammar support for symbol-aware chunking in [`rekipedia.rag.embedder`](src/rekipedia/rag/embedder.py#L1) |
| `tree_sitter_typescript` | not pinned in analysis | TypeScript grammar support in [`rekipedia.rag.embedder`](src/rekipedia/rag/embedder.py#L1) |
| `tree_sitter_go` | not pinned in analysis | Go grammar support in [`rekipedia.rag.embedder`](src/rekipedia/rag/embedder.py#L1) |
| `fastapi` | not pinned in analysis | HTTP server framework for [`create_app`](src/rekipedia/server/app.py#L21) |
| `markdown` | not pinned in analysis | Markdown-to-HTML rendering in [`create_app`](src/rekipedia/server/app.py#L21) |
| `pyturso` / `turso` | optional, not pinned in analysis | Turso-backed SQLite access in [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39), with fallback to stdlib `sqlite3` |
| `cobra` (Go) | not pinned in analysis | Go CLI command framework in [`Execute`](go/cmd/rekipedia/cmd/root.go#L44) and [`openStore`](go/cmd/rekipedia/cmd/note.go#L101) |
| `pterm` (Go) | not pinned in analysis | Terminal banner/output in [`printRootBanner`](go/cmd/rekipedia/cmd/root.go#L36) |
| `modernc.org/sqlite` (Go) | not pinned in analysis | SQLite driver for Go storage in [`go/internal/storage/store.go`](go/internal/storage/store.go#L1) |

The repository metadata shows package versions `0.10.9` for both npm and Python artifacts in the recorded evidence.

> **Sources:** `go/cmd/rekipedia/cmd/root.go` · L36–L78 · [`printRootBanner`](go/cmd/rekipedia/cmd/root.go#L36), [`Execute`](go/cmd/rekipedia/cmd/root.go#L44); `go/cmd/rekipedia/cmd/note.go` · L101–L116 · [`openStore`](go/cmd/rekipedia/cmd/note.go#L101); `go/internal/storage/store.go` · L18–L453 · [`Store`](go/internal/storage/store.go#L18); `src/rekipedia/cli/embed.py` · L22–L201 · [`_check_rag_deps`](src/rekipedia/cli/embed.py#L22), [`embed_cmd`](src/rekipedia/cli/embed.py#L85); `src/rekipedia/rag/embedder.py` · L45–L892 · [`_mmr`](src/rekipedia/rag/embedder.py#L45), [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443); `src/rekipedia/server/app.py` · L21–L663 · [`create_app`](src/rekipedia/server/app.py#L21); `src/rekipedia/storage/sqlite_store.py` · L39–L827 · [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39); `pyproject.toml`; `package.json`

## Integrations

This section describes external systems and services that the project explicitly integrates with.

### LLM Providers via LiteLLM

The project’s LLM integration is mediated through [`litellm`](src/rekipedia/rag/embedder.py#L1) and the client-facing orchestration code in [`rekipedia.orchestrator.run_ask`](src/rekipedia/orchestrator/run_ask.py#L1), [`rekipedia.orchestrator.run_digest`](src/rekipedia/orchestrator/run_digest.py#L1), and [`rekipedia.orchestrator.run_update`](src/rekipedia/orchestrator/run_update.py#L1). The embed pipeline also uses [`_embed_batch`](src/rekipedia/rag/embedder.py#L416) to produce embeddings with `litellm.embedding()`.

- **What it does:** generates chat completions, query rewrites, answer synthesis, and vector embeddings.
- **How it’s configured:** via `llm_config` parameters passed to [`embed_cmd`](src/rekipedia/cli/embed.py#L85), [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L304), [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45), and [`run_update`](src/rekipedia/orchestrator/run_update.py#L27). The code notes a `base_url` can be passed to `litellm` as `api_base` in [`_embed_batch`](src/rekipedia/rag/embedder.py#L416), which indicates compatibility with proxy endpoints.
- **Code reference:** [`_embed_batch`](src/rekipedia/rag/embedder.py#L416), [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L304), [`stream_ask`](src/rekipedia/orchestrator/run_ask.py#L333), [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45), [`run_update`](src/rekipedia/orchestrator/run_update.py#L27)

### FAISS Vector Search Index

The RAG subsystem depends on [`faiss`](src/rekipedia/rag/embedder.py#L1) for indexing and search. [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443) builds an index over chunk embeddings and later searches it for query retrieval.

- **What it does:** stores and searches chunk embeddings for repository-aware retrieval.
- **How it’s configured:** the CLI checks for the dependency in [`_check_rag_deps`](src/rekipedia/cli/embed.py#L22), and the pipeline persists index metadata under the chosen output directory in [`EmbedPipeline.build`](src/rekipedia/rag/embedder.py#L477) and [`EmbedPipeline.update`](src/rekipedia/rag/embedder.py#L733).
- **Code reference:** [`EmbedPipeline.build`](src/rekipedia/rag/embedder.py#L477), [`EmbedPipeline.search`](src/rekipedia/rag/embedder.py#L610), [`EmbedPipeline.update`](src/rekipedia/rag/embedder.py#L733)

### Tree-sitter Grammar Stack

[`rekipedia.rag.embedder`](src/rekipedia/rag/embedder.py#L1) imports `tree_sitter` plus grammars for Python, TypeScript, and Go. The AST-driven path is implemented in [`_symbol_chunk_file_inner`](src/rekipedia/rag/embedder.py#L235).

- **What it does:** performs symbol-aware chunking so embeddings can align to functions/classes/methods instead of arbitrary character windows.
- **How it’s configured:** the code falls back automatically if tree-sitter is missing, the file type is unsupported, or parsing fails. That fallback behavior is documented in [`_symbol_chunk_file`](src/rekipedia/rag/embedder.py#L218).
- **Code reference:** [`_symbol_chunk_file`](src/rekipedia/rag/embedder.py#L218), [`_symbol_chunk_file_inner`](src/rekipedia/rag/embedder.py#L235), [`_chunk_file`](src/rekipedia/rag/embedder.py#L160)

### FastAPI Web Server

The server integration is built around [`create_app`](src/rekipedia/server/app.py#L21), which returns a configured `FastAPI` application.

- **What it does:** serves wiki pages, note pages, JSON endpoints, and streaming ask flows.
- **How it’s configured:** the application factory takes `repo_root`, `output_dir`, and `llm_config`. It also wires Jinja templates, Markdown rendering, and route handlers for note CRUD and Q&A flows.
- **Code reference:** [`create_app`](src/rekipedia/server/app.py#L21)

### SQLite / Turso Storage

The Python store wraps a database connection in [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39). Its docstring states it “uses Turso (pyturso) when available; falls back to stdlib sqlite3.”

- **What it does:** persists scan runs, files, symbols, relationships, pages, notes, QA history, and RAG provenance.
- **How it’s configured:** by constructing [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39) with a database path and calling [`open`](src/rekipedia/storage/sqlite_store.py#L64), or using it as a context manager.
- **Code reference:** [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39), [`SqliteStore.open`](src/rekipedia/storage/sqlite_store.py#L64), [`SqliteStore.upsert_note`](src/rekipedia/storage/sqlite_store.py#L631), [`SqliteStore.upsert_rag_chunks`](src/rekipedia/storage/sqlite_store.py#L710)

### Go CLI and Storage Path

The Go side of the repository also integrates with external packages. [`go/cmd/rekipedia/cmd/root.go`](go/cmd/rekipedia/cmd/root.go#L1) uses `cobra` and `pterm`, and [`go/internal/storage/store.go`](go/internal/storage/store.go#L1) uses `modernc.org/sqlite`.

- **What it does:** provides a Go-based CLI wrapper and storage access layer.
- **How it’s configured:** via Cobra command initialization in [`init`](go/cmd/rekipedia/cmd/root.go#L50) and storage opening/migrations in [`Open`](go/internal/storage/store.go#L24) and [`(s *Store).migrate`](go/internal/storage/store.go#L48).
- **Code reference:** [`Execute`](go/cmd/rekipedia/cmd/root.go#L44), [`openStore`](go/cmd/rekipedia/cmd/note.go#L101), [`Open`](go/internal/storage/store.go#L24), [`(s *Store).migrate`](go/internal/storage/store.go#L48)

> **Sources:** `src/rekipedia/rag/embedder.py` · L1–L892 · [`_embed_batch`](src/rekipedia/rag/embedder.py#L416), [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443), [`_symbol_chunk_file`](src/rekipedia/rag/embedder.py#L218); `src/rekipedia/cli/embed.py` · L22–L201 · [`_check_rag_deps`](src/rekipedia/cli/embed.py#L22), [`embed_cmd`](src/rekipedia/cli/embed.py#L85); `src/rekipedia/server/app.py` · L21–L663 · [`create_app`](src/rekipedia/server/app.py#L21); `src/rekipedia/storage/sqlite_store.py` · L39–L827 · [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39), [`SqliteStore.open`](src/rekipedia/storage/sqlite_store.py#L64), [`SqliteStore.upsert_note`](src/rekipedia/storage/sqlite_store.py#L631); `go/cmd/rekipedia/cmd/root.go` · L36–L78 · [`printRootBanner`](go/cmd/rekipedia/cmd/root.go#L36), [`Execute`](go/cmd/rekipedia/cmd/root.go#L44); `go/internal/storage/store.go` · L18–L119 · [`Open`](go/internal/storage/store.go#L24), [`(s *Store).migrate`](go/internal/storage/store.go#L48)

## Extension Points

The repository does not appear to have a formal plugin registry, but it does expose several extension-like mechanisms that function as stable integration points.

### CLI Subcommands

The Python CLI entry point [`main`](src/rekipedia/cli/__init__.py#L26) wires a `click` command group and imports a suite of subcommand modules from `rekipedia.cli.*`. Even though many of those subcommand files are not present in the analysis snapshot, the import list makes the extension surface clear: commands like `ask`, `embed`, `scan`, `serve`, `update`, `refactor`, `search`, `watch`, and `note` are structured as independent modules.

- **Extension value:** adding a new CLI capability likely means adding a module and importing it in [`rekipedia.cli.__init__`](src/rekipedia/cli/__init__.py#L1).
- **Evidence:** imports of `rekipedia.cli.ask`, `rekipedia.cli.export`, `rekipedia.cli.scan`, `rekipedia.cli.serve`, `rekipedia.cli.update`, and others from [`rekipedia.cli.__init__`](src/rekipedia/cli/__init__.py#L1).

### Note Import Formats

[`import_notes_from_file`](src/rekipedia/notes/__init__.py#L7) is a clear extension point for content ingestion. It routes to [`_import_yaml`](src/rekipedia/notes/__init__.py#L22) or [`_import_markdown`](src/rekipedia/notes/__init__.py#L43), where Markdown sections are parsed into note dictionaries.

- **Extension value:** new import formats could be added as additional helper functions and branches in [`import_notes_from_file`](src/rekipedia/notes/__init__.py#L7).
- **Observable behavior:** Markdown parsing treats each `## Section` as a note, which is a structured contract for inbound content.

### RAG Chunking Strategy

The embedding subsystem has a built-in fallback chain:
- [`_symbol_chunk_file`](src/rekipedia/rag/embedder.py#L218) tries AST-aware chunking
- [`_chunk_file`](src/rekipedia/rag/embedder.py#L160) provides character-based fallback

- **Extension value:** additional language grammars or chunking heuristics can be introduced without changing the public [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443) API.
- **Observable hooks:** the `_is_implementation` heuristic is explicitly called out as “borrowed from deepwiki-open’s data_pipeline.py,” suggesting this area is intended to be adapted and refined.

### Query Rewriting and Retrieval

[`_rewrite_query`](src/rekipedia/orchestrator/run_ask.py#L149) silently rewrites a question into repo vocabulary when possible. The query pipeline also layers page ranking and RAG chunk retrieval through [`_rank_pages_by_query`](src/rekipedia/orchestrator/run_ask.py#L137) and [`_rag_chunks`](src/rekipedia/orchestrator/run_ask.py#L86).

- **Extension value:** the query pipeline can be enhanced by replacing the rewrite logic, score heuristics, or retrieval sources.
- **Observability:** the code already cleanly separates loading wiki pages, symbol lines, and RAG chunks, which are natural seams for experimentation.

### Storage Schema and Migration System

[`SqliteStore._apply_migrations`](src/rekipedia/storage/sqlite_store.py#L117) loads migration files and applies them in order. The analyzed repository includes migration files such as:
- [`003_tech_lead_notes.sql`](src/rekipedia/storage/migrations/003_tech_lead_notes.sql)
- [`004_rag_chunk_provenance.sql`](src/rekipedia/storage/migrations/004_rag_chunk_provenance.sql)
- [`005_page_sources.sql`](src/rekipedia/storage/migrations/005_page_sources.sql)

- **Extension value:** new database capabilities can be added by appending a migration file and corresponding store methods.
- **Important constraint:** since schemas are read from numbered migrations, migration ordering is part of the extension contract.

> **Sources:** `src/rekipedia/cli/__init__.py` · L1–L27 · [`main`](src/rekipedia/cli/__init__.py#L26); `src/rekipedia/notes/__init__.py` · L7–L80 · [`import_notes_from_file`](src/rekipedia/notes/__init__.py#L7), [`_import_yaml`](src/rekipedia/notes/__init__.py#L22), [`_import_markdown`](src/rekipedia/notes/__init__.py#L43); `src/rekipedia/rag/embedder.py` · L160–L232 · [`_chunk_file`](src/rekipedia/rag/embedder.py#L160), [`_symbol_chunk_file`](src/rekipedia/rag/embedder.py#L218); `src/rekipedia/orchestrator/run_ask.py` · L86–L205 · [`_rag_chunks`](src/rekipedia/orchestrator/run_ask.py#L86), [`_rank_pages_by_query`](src/rekipedia/orchestrator/run_ask.py#L137), [`_rewrite_query`](src/rekipedia/orchestrator/run_ask.py#L149); `src/rekipedia/storage/sqlite_store.py` · L117–L131 · [`SqliteStore._apply_migrations`](src/rekipedia/storage/sqlite_store.py#L117); `src/rekipedia/storage/migrations/003_tech_lead_notes.sql`; `src/rekipedia/storage/migrations/004_rag_chunk_provenance.sql`; `src/rekipedia/storage/migrations/005_page_sources.sql`

## Related Projects

The analysis data includes one explicit ecosystem reference in code: [`_is_implementation`](src/rekipedia/rag/embedder.py#L132) says its heuristic was “borrowed from deepwiki-open’s data_pipeline.py.” That is the strongest evidence of a related project in this repository snapshot.

From the overall architecture and naming, this project is in the same space as:
- repo-to-wiki synthesis tools
- codebase understanding / “deep wiki” generators
- RAG-backed documentation assistants

However, to stay within evidence, the only directly cited related project is **deepwiki-open**.

The repository’s own documentation and naming also reinforce this positioning:
- package description in [`main`](src/rekipedia/cli/__init__.py#L26): “rekipedia — agentic repo-to-wiki knowledge store.”
- the `README.md` and release notes are present, but their internal contents were not exposed in the analysis payload beyond file existence, so no additional named comparisons can be safely inferred here.

> **Sources:** `src/rekipedia/rag/embedder.py` · L132–L141 · [`_is_implementation`](src/rekipedia/rag/embedder.py#L132); `src/rekipedia/cli/__init__.py` · L26–L27 · [`main`](src/rekipedia/cli/__init__.py#L26); `README.md`; `RELEASE-NOTES.md`

## Roadmap / Known Limitations

The analysis payload did not include explicit `TODO` or `FIXME` tokens, and the `risks` array is empty. Still, the code and test coverage reveal several practical limitations and follow-up areas.

### 1. Dependency fallback and optionality are uneven

[`_check_rag_deps`](src/rekipedia/cli/embed.py#L22) suggests `faiss-cpu` and `numpy` are optional at runtime and may be missing. The CLI responds with a friendly error, but this still means the embedding path is partially optional and can fail early if the environment is not prepared.

### 2. Some internal helpers lack test coverage

The analysis explicitly flags the following as knowledge gaps:
- [`_now`](src/rekipedia/storage/sqlite_store.py#L832)
- [`_get_store`](src/rekipedia/cli/note.py#L16)
- [`_embed_batch`](src/rekipedia/rag/embedder.py#L416)
- [`_combine_results`](src/rekipedia/orchestrator/run_digest.py#L436)

This is a strong indicator of risk around time formatting, store resolution, embedding API behavior, and result aggregation.

### 3. Incremental and targeted workflows are still evolving

The update pipeline, especially [`run_update`](src/rekipedia/orchestrator/run_update.py#L27), appears quite sophisticated: it copies unchanged symbols, carries forward page sources, and can trigger incremental RAG updates. The presence of tests like `test_targeted_wiki_resynthesis_only_affected_pages` and `test_update_triggers_incremental_rag_embed_when_index_exists` indicates active work in this area, and the design suggests ongoing refinement rather than a frozen API.

### 4. Cross-language storage surface is duplicated

There is a Go storage layer (`go/internal/storage/store.go`) and a Python storage layer ([`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39)). The analysis does not show a unifying abstraction across them. That duplication is not inherently wrong, but it means schema evolution, migration semantics, and feature parity can diverge.

### 5. Related-project borrowing may need clearer attribution

Since [`_is_implementation`](src/rekipedia/rag/embedder.py#L132) explicitly references deepwiki-open as inspiration, attribution and provenance may be worth keeping clear if this code is upstreamed, redistributed, or compared in docs.

> **Sources:** `src/rekipedia/cli/embed.py` · L22–L41 · [`_check_rag_deps`](src/rekipedia/cli/embed.py#L22); `src/rekipedia/storage/sqlite_store.py` · L832–L833 · [`_now`](src/rekipedia/storage/sqlite_store.py#L832); `src/rekipedia/cli/note.py` · L16–L23 · [`_get_store`](src/rekipedia/cli/note.py#L16); `src/rekipedia/rag/embedder.py` · L416–L436 · [`_embed_batch`](src/rekipedia/rag/embedder.py#L416); `src/rekipedia/orchestrator/run_digest.py` · L436–L450 · [`_combine_results`](src/rekipedia/orchestrator/run_digest.py#L436); `src/rekipedia/rag/embedder.py` · L132–L141 · [`_is_implementation`](src/rekipedia/rag/embedder.py#L132); `src/rekipedia/orchestrator/run_update.py` · L27–L244 · [`run_update`](src/rekipedia/orchestrator/run_update.py#L27)

## Summary

The project integrates with a fairly standard but powerful stack: Click for CLI, FastAPI for serving, SQLite/Turso for persistence, FAISS for vector search, LiteLLM for model access, and tree-sitter for syntax-aware chunking. Its extension points are mostly architectural rather than formal plugin APIs: command modules, import format handlers, chunking strategies, migration files, and query-ranking logic.

The strongest externally referenced ecosystem signal is the explicit borrowing from **deepwiki-open**, which places this repository squarely in the “repo understanding and documentation synthesis” space.

> **Sources:** `src/rekipedia/cli/__init__.py` · L26–L27 · [`main`](src/rekipedia/cli/__init__.py#L26); `src/rekipedia/server/app.py` · L21–L21 · [`create_app`](src/rekipedia/server/app.py#L21); `src/rekipedia/storage/sqlite_store.py` · L39–L39 · [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39); `src/rekipedia/rag/embedder.py` · L1–L892 · [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443)