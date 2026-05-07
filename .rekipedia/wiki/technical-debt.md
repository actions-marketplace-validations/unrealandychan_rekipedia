---
slug: technical-debt
title: "Technical Debt Audit"
section: general
pin: false
importance: 50
created_at: 2026-05-07T04:13:30Z
rekipedia_version: 0.10.9
---

# Technical Debt Audit

## Summary

This codebase is functionally broad and well-covered in several critical areas, especially around notes, RAG chunking, and update workflows, but it also shows signs of accumulating architectural and maintenance debt. The overall debt rating is **Medium**: the system has solid test coverage for key paths, yet a few large “orchestrator” and “server” modules have very high complexity, significant coupling, and repeated patterns that will slow future change.

The most notable risks are concentrated in [`create_app`](src/rekipedia/server/app.py#L21), [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45), [`run_update`](src/rekipedia/orchestrator/run_update.py#L27), [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443), and [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39). These components are highly connected hubs in the dependency graph, which means defects or design changes there will have outsized impact across the application.

> **Sources:** `src/rekipedia/server/app.py` · L21–L663 · [`create_app`](src/rekipedia/server/app.py#L21) · `src/rekipedia/orchestrator/run_digest.py` · L45–L433 · [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45) · `src/rekipedia/orchestrator/run_update.py` · L27–L244 · [`run_update`](src/rekipedia/orchestrator/run_update.py#L27) · `src/rekipedia/rag/embedder.py` · L443–L892 · [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443) · `src/rekipedia/storage/sqlite_store.py` · L39–L827 · [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39)

## Debt Inventory

| # | Area | Severity | Description | Files Affected | Effort to Fix |
|---|------|----------|-------------|----------------|---------------|
| 1 | `create_app` complexity | 🔴 Critical | Massive FastAPI factory with routing, rendering, note persistence, Q&A, wiki serving, streaming, and repo metadata logic all in one function. | `src/rekipedia/server/app.py` | XL |
| 2 | `run_digest` pipeline monolith | 🔴 Critical | Large end-to-end scan pipeline handles snapshotting, sharding, extraction, page synthesis, diagrams, exports, RAG embedding, and status updates. | `src/rekipedia/orchestrator/run_digest.py` | XL |
| 3 | `run_update` pipeline monolith | 🔴 Critical | Incremental update path duplicates much of the full scan orchestration and includes many responsibilities in one function. | `src/rekipedia/orchestrator/run_update.py` | XL |
| 4 | `EmbedPipeline` size and branching | 🟠 High | One class owns chunking, embedding, FAISS index lifecycle, search, and incremental update logic. | `src/rekipedia/rag/embedder.py` | L |
| 5 | `SqliteStore` god object | 🟠 High | Database wrapper exposes a very large API across runs, files, symbols, pages, QA, notes, and RAG provenance. | `src/rekipedia/storage/sqlite_store.py` | XL |
| 6 | Complex Markdown/YAML import logic | 🟠 High | Note import parsing is split across multiple helpers with weak explicit schema validation. | `src/rekipedia/notes/__init__.py`, `src/rekipedia/cli/note.py` | M |
| 7 | Duplicate note storage access patterns | 🟡 Medium | CLI and server both implement store-open / store-close workflows and similar filtering/selection logic. | `src/rekipedia/cli/note.py`, `src/rekipedia/server/app.py`, `src/rekipedia/storage/sqlite_store.py` | M |
| 8 | Repeated “fallback” control flow | 🟡 Medium | Several functions include fallback-to-default behavior without shared helper abstraction. | `src/rekipedia/rag/embedder.py`, `src/rekipedia/orchestrator/run_ask.py`, `src/rekipedia/server/app.py` | M |
| 9 | Low-level string parsing utilities | 🟡 Medium | Custom tag / comma / whitespace splitting utilities indicate schema normalization concerns are leaking into storage layer. | `src/rekipedia/storage/store.go` | S |
| 10 | Sparse tests for core helpers | 🟡 Medium | A few frequently used helpers are not directly covered, especially internal store/pipeline helpers. | `src/rekipedia/storage/sqlite_store.py`, `src/rekipedia/cli/note.py`, `src/rekipedia/rag/embedder.py`, `src/rekipedia/orchestrator/run_digest.py` | S–M |

> **Sources:** `src/rekipedia/server/app.py` · L21–L663 · [`create_app`](src/rekipedia/server/app.py#L21) · `src/rekipedia/orchestrator/run_digest.py` · L45–L433 · [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45) · `src/rekipedia/orchestrator/run_update.py` · L27–L244 · [`run_update`](src/rekipedia/orchestrator/run_update.py#L27) · `src/rekipedia/rag/embedder.py` · L443–L892 · [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443) · `src/rekipedia/storage/sqlite_store.py` · L39–L827 · [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39) · `src/rekipedia/notes/__init__.py` · L7–L80 · [`import_notes_from_file`](src/rekipedia/notes/__init__.py#L7) · `src/rekipedia/cli/note.py` · L16–L153 · [`note_import`](src/rekipedia/cli/note.py#L127)

## Critical Issues

### 1) `create_app` is doing too much

[`create_app`](src/rekipedia/server/app.py#L21) spans the entire FastAPI application setup and appears to inline route definitions, HTML rendering, note CRUD, Q&A persistence, wiki-page listing, streaming response handling, and metadata loading. The analysis reports an out-degree of **307** for this function, which is a strong indicator of an overloaded orchestration function.

**Why this is a problem**

- Hard to reason about or safely modify.
- Very expensive to test in isolation.
- Changes to one route can accidentally affect unrelated behavior.
- Increases merge conflict risk because many concerns share one file/function.

**Concrete fix**

Split the factory into route registration helpers and service-level helpers, for example:

```python
def create_app(repo_root, output_dir, llm_config):
    app = FastAPI()
    register_wiki_routes(app, repo_root, output_dir, llm_config)
    register_note_routes(app, output_dir)
    register_qa_routes(app, repo_root, output_dir, llm_config)
    return app
```

Then move the route bodies into dedicated functions or submodules, such as `server/routes/wiki.py`, `server/routes/notes.py`, and `server/routes/qa.py`.

> **Sources:** `src/rekipedia/server/app.py` · L21–L663 · [`create_app`](src/rekipedia/server/app.py#L21) · `tests/test_notes_server.py` · L15–L66 · [`app`](tests/test_notes_server.py#L15)

### 2) `run_digest` is a pipeline monolith

[`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45) orchestrates nearly every major subsystem: snapshotting, sharding, sandbox execution, analysis aggregation, page synthesis, diagram generation, export, scan metadata, agent hints, MCP JSON, gitignore updates, refactor outputs, and RAG embedding. The function spans hundreds of lines and is the central bridge node in the dependency graph.

**Why this is a problem**

- Extremely high cognitive load.
- Difficult to reuse parts of the pipeline.
- Any failure path is likely to be entangled with cleanup/status logic.
- The function is effectively the “application kernel,” but without clear phase boundaries.

**Concrete fix**

Introduce explicit pipeline stages with a coordinator object:

```python
class DigestPipeline:
    def snapshot(self): ...
    def analyze(self): ...
    def synthesize(self): ...
    def export(self): ...
    def embed(self): ...
```

Keep `run_digest()` as a thin wrapper around a stage runner. This also makes it easier to parallelize or mock stages independently.

> **Sources:** `src/rekipedia/orchestrator/run_digest.py` · L45–L433 · [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45) · `src/rekipedia/storage/sqlite_store.py` · L137–L217 · [`SqliteStore.upsert_run`](src/rekipedia/storage/sqlite_store.py#L137) · [`SqliteStore.upsert_file`](src/rekipedia/storage/sqlite_store.py#L194)

### 3) `run_update` duplicates orchestration concerns

[`run_update`](src/rekipedia/orchestrator/run_update.py#L27) mirrors many responsibilities from the digest pipeline: it opens the store, checks the latest run, snapshots, reuses or copies unchanged data, rebuilds pages and diagrams, performs exports, and conditionally updates RAG embeddings. It is smaller than `run_digest`, but still too large for a single function.

**Why this is a problem**

- Incremental logic is split between two large orchestration functions.
- Hard to ensure parity between full scan and update behavior.
- Changes to one pipeline likely need changes in the other.

**Concrete fix**

Extract shared orchestration primitives like:

- `load_previous_scan_state()`
- `build_wiki_for_run()`
- `refresh_rag_index()`
- `persist_pipeline_status()`

Then let both `run_digest()` and `run_update()` compose those primitives.

> **Sources:** `src/rekipedia/orchestrator/run_update.py` · L27–L244 · [`run_update`](src/rekipedia/orchestrator/run_update.py#L27) · `src/rekipedia/orchestrator/run_digest.py` · L45–L433 · [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45)

### 4) `EmbedPipeline` combines too many concerns

[`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443) owns file iteration, chunking, AST-aware chunking fallback, embedding API access, FAISS indexing, metadata persistence, search, and incremental update behavior. This is a classic “pipeline class” that has grown into a mini-framework.

**Why this is a problem**

- Too many reasons to change.
- Hard to test chunking independent from FAISS or remote embedding APIs.
- Search/update logic is interwoven with persistence and file-system behavior.

**Concrete fix**

Split into smaller collaborators:

- `RepoChunker`
- `EmbeddingClient`
- `VectorIndexStore`
- `RagSearchService`

Keep `EmbedPipeline` as a façade only if needed.

> **Sources:** `src/rekipedia/rag/embedder.py` · L443–L892 · [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443) · [`EmbedPipeline.build`](src/rekipedia/rag/embedder.py#L477) · [`EmbedPipeline.search`](src/rekipedia/rag/embedder.py#L610) · [`EmbedPipeline.update`](src/rekipedia/rag/embedder.py#L733)

### 5) `SqliteStore` is a database god object

[`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39) exposes a very wide API: run lifecycle, snapshot files, symbols, relationships, pages, diagrams, Q&A history, notes, RAG provenance, page-source mappings, and incremental copy/carry-forward methods. The breadth is reflected in the symbol list and in the dependency graph, where it is one of the most central classes.

**Why this is a problem**

- Very high surface area for regressions.
- Database schema and domain logic are tightly coupled.
- Schema evolution becomes risky because the class is responsible for too many tables and operations.

**Concrete fix**

Split the store by bounded contexts:

- `RunStore`
- `WikiStore`
- `NotesStore`
- `RagStore`

Then compose them from a connection manager. This preserves the current persistence backend while reducing the class size dramatically.

> **Sources:** `src/rekipedia/storage/sqlite_store.py` · L39–L827 · [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39)

## Code Smell Patterns

### God objects / mega-functions

The clearest recurring smell is “everything in one place.” [`create_app`](src/rekipedia/server/app.py#L21), [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45), [`run_update`](src/rekipedia/orchestrator/run_update.py#L27), [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443), and [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39) all act as hubs with very high out-degree or massive method counts.

**Recommended refactor:** split by responsibility and expose smaller composable services.

> **Sources:** `src/rekipedia/server/app.py` · L21–L663 · [`create_app`](src/rekipedia/server/app.py#L21) · `src/rekipedia/orchestrator/run_digest.py` · L45–L433 · [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45) · `src/rekipedia/orchestrator/run_update.py` · L27–L244 · [`run_update`](src/rekipedia/orchestrator/run_update.py#L27) · `src/rekipedia/rag/embedder.py` · L443–L892 · [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443) · `src/rekipedia/storage/sqlite_store.py` · L39–L827 · [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39)

### Repeated fallback logic

Fallbacks are explicit in the RAG and query paths: [`_symbol_chunk_file`](src/rekipedia/rag/embedder.py#L218) falls back to [`_chunk_file`](src/rekipedia/rag/embedder.py#L160), [`_rewrite_query`](src/rekipedia/orchestrator/run_ask.py#L149) silently returns the original query if rewriting fails, and `EmbedPipeline.update()` falls back to `build()` when no existing index exists. The logic is sensible, but repeated, which makes behavior harder to reason about consistently.

**Recommended refactor:** move fallback decisions into shared strategy helpers, and surface more explicit status values instead of silent branch changes.

> **Sources:** `src/rekipedia/rag/embedder.py` · L160–L232 · [`_chunk_file`](src/rekipedia/rag/embedder.py#L160) · [`_symbol_chunk_file`](src/rekipedia/rag/embedder.py#L218) · `src/rekipedia/orchestrator/run_ask.py` · L149–L205 · [`_rewrite_query`](src/rekipedia/orchestrator/run_ask.py#L149) · `src/rekipedia/rag/embedder.py` · L733–L892 · [`EmbedPipeline.update`](src/rekipedia/rag/embedder.py#L733)

### Manual parsing helpers in storage code

The Go storage layer includes low-level helpers like [`splitTags`](go/internal/storage/store.go#L418), [`splitByComma`](go/internal/storage/store.go#L432), and [`trimSpace`](go/internal/storage/store.go#L445). These indicate the storage layer is compensating for normalization or formatting issues in upstream data.

**Recommended refactor:** normalize this data at the input boundary or use a typed representation before persistence.

> **Sources:** `go/internal/storage/store.go` · L418–L453 · [`splitTags`](go/internal/storage/store.go#L418) · [`splitByComma`](go/internal/storage/store.go#L432) · [`trimSpace`](go/internal/storage/store.go#L445)

### Large helper clusters with no direct coverage

Several helpers are exercised indirectly but are not directly covered by dedicated tests, including [`_get_store`](src/rekipedia/cli/note.py#L16), [`_embed_batch`](src/rekipedia/rag/embedder.py#L416), [`_combine_results`](src/rekipedia/orchestrator/run_digest.py#L436), and [`_now`](src/rekipedia/storage/sqlite_store.py#L832). These are small, but they sit on core paths and are vulnerable to regression.

**Recommended refactor:** add focused unit tests for edge cases and failure modes.

> **Sources:** `src/rekipedia/cli/note.py` · L16–L23 · [`_get_store`](src/rekipedia/cli/note.py#L16) · `src/rekipedia/rag/embedder.py` · L416–L436 · [`_embed_batch`](src/rekipedia/rag/embedder.py#L416) · `src/rekipedia/orchestrator/run_digest.py` · L436–L450 · [`_combine_results`](src/rekipedia/orchestrator/run_digest.py#L436) · `src/rekipedia/storage/sqlite_store.py` · L832–L833 · [`_now`](src/rekipedia/storage/sqlite_store.py#L832)

## Missing Tests

The repository’s visible test suite is reasonably strong around notes, RAG, and update behavior, but the analysis explicitly identifies several untested helpers with real call counts. Based on `test_file_count` vs. `impl_file_count` and the provided `knowledge_gaps`, the most obvious gaps are:

| Function | File | Reason |
|---|---|---|
| `_now` | `src/rekipedia/storage/sqlite_store.py` | Called 7 times, no direct test coverage |
| `_get_store` | `src/rekipedia/cli/note.py` | Called 5 times, no direct test coverage |
| `_embed_batch` | `src/rekipedia/rag/embedder.py` | Called 4 times, no direct test coverage |
| `_combine_results` | `src/rekipedia/orchestrator/run_digest.py` | Called 3 times, no direct test coverage |

The test suite does cover many neighboring behaviors, such as note CRUD, RAG chunking, and update flows, but these helpers are good candidates for small, fast unit tests because they are logic-heavy and easy to isolate.

**Specific modules/functions that would benefit from tests**
- `src/rekipedia/cli/note.py`: `_get_store`, `note_edit`, `note_import`
- `src/rekipedia/rag/embedder.py`: `_embed_batch`, `_mmr`, `EmbedPipeline.search`
- `src/rekipedia/orchestrator/run_digest.py`: `_combine_results`
- `src/rekipedia/storage/sqlite_store.py`: `_now`, migration/application behavior in `_apply_migrations`

> **Sources:** `src/rekipedia/storage/sqlite_store.py` · L832–L833 · [`_now`](src/rekipedia/storage/sqlite_store.py#L832) · `src/rekipedia/cli/note.py` · L16–L23 · [`_get_store`](src/rekipedia/cli/note.py#L16) · `src/rekipedia/rag/embedder.py` · L416–L436 · [`_embed_batch`](src/rekipedia/rag/embedder.py#L416) · `src/rekipedia/orchestrator/run_digest.py` · L436–L450 · [`_combine_results`](src/rekipedia/orchestrator/run_digest.py#L436)

## Dependency & Security Concerns

No explicit dependency risk list was provided in the analysis payload, and the `risks` array is empty. The available metadata does, however, show a set of potentially security-sensitive or operationally risky dependencies:

| Dependency | Location | Concern |
|---|---|---|
| `faiss` / `faiss-cpu` | `src/rekipedia/cli/embed.py`, `src/rekipedia/rag/embedder.py` | Native dependency; versioning and binary compatibility can be fragile |
| `tree_sitter*` parsers | `src/rekipedia/rag/embedder.py` | Native parsing stack increases install and runtime risk |
| `litellm` | `src/rekipedia/orchestrator/run_ask.py`, `src/rekipedia/rag/embedder.py`, `src/rekipedia/orchestrator/run_digest.py` | External API routing and provider configuration must be carefully controlled |
| `modernc.org/sqlite` | `go/internal/storage/store.go` | Embedded database driver; usually safe, but version drift matters |
| `turso` / `pyturso` | `src/rekipedia/storage/sqlite_store.py` | Optional DB backend adds another supply-chain and compatibility surface |

Because the actual `package.json` / `pyproject.toml` contents were not included in the analysis payload, I cannot safely name specific versions as outdated or CVE-prone. Likewise, I cannot claim known CVEs without package-version evidence. The best evidenced concern is that the codebase depends on a fairly large stack of native and networked libraries, so dependency pinning and periodic auditing should be treated as important operational work.

**Recommended action**
- Pin all runtime dependencies explicitly.
- Add automated dependency scanning in CI.
- Review optional native packages (`faiss`, `tree_sitter`, SQLite backends) for platform support and security posture.

> **Sources:** `src/rekipedia/cli/embed.py` · L1–L201 · [`embed_cmd`](src/rekipedia/cli/embed.py#L85) · `src/rekipedia/rag/embedder.py` · L1–L901 · [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443) · `src/rekipedia/orchestrator/run_digest.py` · L1–L450 · [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45) · `src/rekipedia/storage/sqlite_store.py` · L1–L827 · [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39)

## TODO / FIXME Tracker

No TODO / FIXME / HACK / XXX comments were included in the analysis payload, so I cannot extract a verified tracker table without risking fabrication.

If you want this section populated, the repo needs a comment scan pass that captures exact file/line text. Based on the current data, the correct answer is: **none evidenced**.

> **Sources:** No TODO/FIXME comments were provided in the analysis payload.

## Refactoring Roadmap

| Priority | Action | Rationale | Estimated Effort |
|----------|--------|-----------|-----------------|
| 1 | Split `create_app` into route modules | Largest maintainability win; immediately reduces complexity in the HTTP layer | XL |
| 2 | Extract shared pipeline stages from `run_digest` and `run_update` | Removes duplication and aligns full/update workflows | XL |
| 3 | Decompose `SqliteStore` into bounded-context stores | Big reduction in coupling and schema-management risk | XL |
| 4 | Break `EmbedPipeline` into chunking, embedding, and index services | Lowers cognitive load and improves testability | L |
| 5 | Add targeted tests for `_now`, `_get_store`, `_embed_batch`, `_combine_results` | Cheap, high-value coverage for core helper logic | S–M |
| 6 | Centralize fallback/error-handling patterns | Makes failure behavior more predictable across RAG and query paths | M |
| 7 | Formalize note import schema validation | Reduces ambiguity and hidden parsing edge cases | M |
| 8 | Audit and pin native/network dependencies | Operational hardening; especially useful before wider deployment | M |

A good sequencing strategy is to start with the high-impact structural splits, then immediately back them with focused unit tests. That gives you safer refactoring for the rest of the codebase and reduces the chance that future changes just move complexity around instead of removing it.

> **Sources:** `src/rekipedia/server/app.py` · L21–L663 · [`create_app`](src/rekipedia/server/app.py#L21) · `src/rekipedia/orchestrator/run_digest.py` · L45–L433 · [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45) · `src/rekipedia/orchestrator/run_update.py` · L27–L244 · [`run_update`](src/rekipedia/orchestrator/run_update.py#L27) · `src/rekipedia/storage/sqlite_store.py` · L39–L827 · [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39) · `src/rekipedia/rag/embedder.py` · L443–L892 · [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443)