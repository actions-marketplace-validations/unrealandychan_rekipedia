---
slug: testing
title: "Testing Strategy and How to Run Tests"
section: general
pin: false
importance: 50
created_at: 2026-05-07T04:12:37Z
rekipedia_version: 0.10.9
---

# Testing Strategy and How to Run Tests

## Testing Philosophy

The repository’s test suite is organised around the main user-facing workflows and the persistence layer that supports them. The current tests emphasize:

- **CLI behavior** for the notes workflow via [`tests.test_notes_cli`](tests/test_notes_cli.py#L1)
- **SQLite storage correctness** via [`tests.test_notes_store`](tests/test_notes_store.py#L1) and RAG persistence tests in [`tests.test_rag`](tests/test_rag.py#L1)
- **HTTP/API and template behavior** via [`tests.test_notes_server`](tests/test_notes_server.py#L1)
- **Incremental update behavior** via [`tests.test_update`](tests/test_update.py#L1)
- **RAG chunking and embedding mechanics** in [`rekipedia.rag.embedder`](src/rekipedia/rag/embedder.py#L443) and its tests

This is a pragmatic, workflow-driven test strategy: instead of trying to exhaustively unit-test every line, the suite focuses on the system boundaries where regressions are most expensive:

- command-line interaction
- database persistence and migrations
- document/chunk provenance
- incremental update semantics
- page regeneration after changes

The evidence also suggests a deliberate emphasis on **fixture-driven, isolated tests**. The test files use temporary directories and lightweight fake responses such as [`_fake_embed_response`](tests/test_rag.py#L65) and [`_fake_llm_response`](tests/test_update.py#L19) to avoid network and external service dependencies. For example, embedding-related tests verify the behavior of [`EmbedPipeline.build`](src/rekipedia/rag/embedder.py#L477) and [`EmbedPipeline.update`](src/rekipedia/rag/embedder.py#L733) without calling a real model backend.

A few implementation gaps are visible in the analysis data:

- [`_now`](src/rekipedia/storage/sqlite_store.py#L832) has no direct test coverage
- [`_get_store`](src/rekipedia/cli/note.py#L16) is not directly tested
- [`_embed_batch`](src/rekipedia/rag/embedder.py#L416) is not directly tested
- [`_combine_results`](src/rekipedia/orchestrator/run_digest.py#L436) is not directly tested

These are not necessarily defects; they simply indicate where the suite currently relies on higher-level tests rather than direct unit tests.

> **Sources:** `tests/test_notes_cli.py` · `tests/test_notes_store.py` · `tests/test_notes_server.py` · `tests/test_notes_rag.py` · `tests/test_rag.py` · `tests/test_update.py` · `src/rekipedia/rag/embedder.py` · L443–L892 · [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443)

## Test Structure

### Directory Layout

The repository’s tests are all under a single top-level `tests/` directory:

| Path | Purpose |
|------|---------|
| `tests/test_notes_cli.py` | CLI behavior for note management |
| `tests/test_notes_store.py` | Store-level CRUD and filtering for notes |
| `tests/test_notes_server.py` | FastAPI route behavior for note pages/API |
| `tests/test_notes_rag.py` | Notes integration with the assembled RAG/system context |
| `tests/test_rag.py` | RAG chunking, provenance, embedding, and store round-trips |
| `tests/test_update.py` | Incremental scan/update pipeline behavior |

This structure is intentionally flat. Rather than splitting by package, the suite groups by **feature area** and **integration surface**:

- **CLI tests** validate commands and output formatting
- **Store tests** validate database methods and migration-backed schema
- **Server tests** validate HTTP endpoints and rendered note pages
- **RAG tests** validate chunking, indexing, and provenance
- **Update tests** validate orchestration and incremental refresh logic

### What Each Test File Covers

- [`tests.test_notes_cli`](tests/test_notes_cli.py#L1): note add/list/remove/edit/import commands, including YAML and Markdown import paths
- [`tests.test_notes_store`](tests/test_notes_store.py#L1): note persistence, tag filtering, update semantics, deletion, and lookup
- [`tests.test_notes_server`](tests/test_notes_server.py#L1): FastAPI routes for notes and notes page rendering
- [`tests.test_notes_rag`](tests/test_notes_rag.py#L1): ensuring notes are injected into assembled system context only when present
- [`tests.test_rag`](tests/test_rag.py#L1): scan metadata, chunk provenance, symbol chunking fallback behavior, FAISS-backed search, and incremental chunk updates
- [`tests.test_update`](tests/test_update.py#L1): fallback from update to full scan, no-op behavior when unchanged, targeted page resynthesis, page source tracking, and incremental RAG re-embedding

> **Sources:** `tests/test_notes_cli.py` · `tests/test_notes_store.py` · `tests/test_notes_server.py` · `tests/test_notes_rag.py` · `tests/test_rag.py` · `tests/test_update.py`

## Running Tests

The only test command recorded in the analysis data is:

```bash
pytest
```

Because the repository exposes a Python package and CLI entry point via [`rekipedia.cli:main`](README.md) and has a `pytest` test suite, the documented test runner is straightforward.

### Recommended Invocations

The task asks for unit, integration, and coverage examples. The analysis data only confirms `pytest`, so the following commands are the safest documented forms while still aligning with standard pytest usage:

```bash
# unit tests
pytest

# integration tests
pytest

# with coverage
pytest --cov=rekipedia --cov-report=term-missing
```

The suite does not currently advertise separate test markers such as `unit` or `integration`, so the same base command is used for both categories. If you add markers later, you can refine these commands without changing the overall test workflow.

### Running a Single Test

You can run a single test module or test case using standard pytest selection syntax:

```bash
pytest tests/test_rag.py
pytest tests/test_update.py::test_update_no_changes_exits_early
pytest tests/test_notes_cli.py::test_note_add
```

### Practical Notes

Because many tests use temporary directories and fakes, they should be deterministic and not require external services. That said, the codebase includes features that can depend on optional packages such as FAISS, numpy, and tree-sitter in production paths; the tests are written to avoid requiring those services directly when possible.

> **Sources:** `pytest` test command from analysis data · `tests/test_rag.py` · `tests/test_update.py` · `tests/test_notes_cli.py`

## Test Categories

### Unit Tests

The suite contains several strong unit-test clusters around pure or near-pure logic:

#### Notes Store
[`tests.test_notes_store`](tests/test_notes_store.py#L1) exercises the methods behind [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39), including:

- note creation and listing
- tag filtering
- update-in-place behavior
- deletion and lookup
- alias behavior such as `get_notes`

These tests are especially valuable because they validate the storage contract without involving the CLI or HTTP layers.

#### RAG Chunking and Provenance
[`tests.test_rag`](tests/test_rag.py#L1) checks chunking and provenance behavior for helpers in [`rekipedia.rag.embedder`](src/rekipedia/rag/embedder.py#L1), including:

- [`_is_implementation`](src/rekipedia/rag/embedder.py#L132) heuristic classification
- [`_chunk_file`](src/rekipedia/rag/embedder.py#L160) line-provenance generation
- [`_symbol_chunk_file`](src/rekipedia/rag/embedder.py#L218) and fallback behavior
- [`EmbedPipeline.search`](src/rekipedia/rag/embedder.py#L610) search output shape
- store round-trips for [`SqliteStore.upsert_rag_chunks`](src/rekipedia/storage/sqlite_store.py#L710) and [`SqliteStore.get_rag_chunks_by_file`](src/rekipedia/storage/sqlite_store.py#L739)

#### Fixtures and Mocks
A few key test fixtures and fake responses are visible:

| Fixture / helper | File | Role |
|---|---|---|
| [`_fake_embed_response`](tests/test_rag.py#L65) | `tests/test_rag.py` | Produces deterministic embedding responses |
| [`_make_test_repo`](tests/test_rag.py#L75) | `tests/test_rag.py` | Builds a small synthetic repository |
| [`mock_llm`](tests/test_update.py#L34) | `tests/test_update.py` | Replaces LLM behavior in update tests |
| [`_fake_llm_response`](tests/test_update.py#L19) | `tests/test_update.py` | Supplies stable LLM output |
| [`runner`](tests/test_notes_cli.py#L14) | `tests/test_notes_cli.py` | Click command runner fixture |
| [`store`](tests/test_notes_store.py#L12) | `tests/test_notes_store.py` | Temporary SQLite-backed store |

The strong pattern here is that tests isolate code under test from model calls, the filesystem beyond a temp tree, and network dependencies.

> **Sources:** `tests/test_notes_store.py` · `tests/test_rag.py` · `tests/test_update.py` · `src/rekipedia/storage/sqlite_store.py` · L39–L827 · [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39) · `src/rekipedia/rag/embedder.py` · L132–L232 · [`_chunk_file`](src/rekipedia/rag/embedder.py#L160) · [`EmbedPipeline.search`](src/rekipedia/rag/embedder.py#L610)

### Integration Tests

Integration coverage focuses on behavior across module boundaries.

#### CLI → Store
[`tests.test_notes_cli`](tests/test_notes_cli.py#L1) drives the note commands from the CLI layer into the store layer via [`note_add`](src/rekipedia/cli/note.py#L35), [`note_list`](src/rekipedia/cli/note.py#L49), [`note_remove`](src/rekipedia/cli/note.py#L70), [`note_edit`](src/rekipedia/cli/note.py#L96), and [`note_import`](src/rekipedia/cli/note.py#L127). This validates the full user-facing behavior rather than just individual store calls.

#### Update Orchestration
[`tests.test_update`](tests/test_update.py#L1) verifies cross-module flows involving:

- [`run_update`](src/rekipedia/orchestrator/run_update.py#L27)
- [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45)
- [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39)
- [`PageBuilder`](src/rekipedia/orchestrator/run_digest.py#L1) as referenced by the scan pipeline
- [`EmbedPipeline.update`](src/rekipedia/rag/embedder.py#L733)

This suite checks that an update can:
1. detect whether a previous scan exists,
2. identify changed files,
3. preserve unchanged symbols and relationships,
4. refresh wiki pages,
5. update the incremental RAG index when an index already exists.

#### Server Routes
[`tests.test_notes_server`](tests/test_notes_server.py#L1) exercises the FastAPI app produced by [`create_app`](src/rekipedia/server/app.py#L21). This covers:

- `GET` notes listing
- `POST` note creation
- `DELETE` note removal
- notes page rendering

#### Notes in RAG Context
[`tests.test_notes_rag`](tests/test_notes_rag.py#L1) validates that notes are included in the assembled system context used by [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L304) and excluded when there are no notes.

> **Sources:** `tests/test_notes_cli.py` · `tests/test_notes_server.py` · `tests/test_notes_rag.py` · `tests/test_update.py` · `src/rekipedia/cli/note.py` · L35–L153 · [`note_add`](src/rekipedia/cli/note.py#L35) · [`note_import`](src/rekipedia/cli/note.py#L127) · `src/rekipedia/orchestrator/run_update.py` · L27–L244 · [`run_update`](src/rekipedia/orchestrator/run_update.py#L27) · `src/rekipedia/server/app.py` · L21–L663 · [`create_app`](src/rekipedia/server/app.py#L21)

## Writing New Tests

### Conventions to Follow

When adding new tests, follow the existing style:

1. **Put the test next to the feature area**
   - CLI note behavior → `tests/test_notes_cli.py`
   - storage behavior → `tests/test_notes_store.py`
   - server routes → `tests/test_notes_server.py`
   - RAG/chunking → `tests/test_rag.py`
   - update pipeline → `tests/test_update.py`

2. **Use temp directories and fakes**
   - Prefer `tmp_path`, temporary stores, and mock responses over real external services
   - Mirror the existing use of [`_fake_embed_response`](tests/test_rag.py#L65) and [`_fake_llm_response`](tests/test_update.py#L19)

3. **Test outcomes, not internals**
   - For example, assert that [`EmbedPipeline.build`](src/rekipedia/rag/embedder.py#L477) persisted chunk provenance or that [`run_update`](src/rekipedia/orchestrator/run_update.py#L27) produced a new run, rather than checking every intermediate branch

4. **Prefer deterministic assertions**
   - The suite commonly checks lengths, returned rows, JSON payloads, and exact note contents

### Where to Put New Tests

| New behavior belongs to... | Suggested file |
|---|---|
| Note CLI command | `tests/test_notes_cli.py` |
| Notes persistence or schema changes | `tests/test_notes_store.py` |
| Notes API/view behavior | `tests/test_notes_server.py` |
| Context assembly / RAG prompt injection | `tests/test_notes_rag.py` |
| Embedding, chunking, provenance, search | `tests/test_rag.py` |
| Scan/update orchestration | `tests/test_update.py` |

### Running a Single New Test

During development, run the narrowest possible selection:

```bash
pytest tests/test_update.py::test_my_new_behavior
pytest tests/test_rag.py -k provenance
pytest tests/test_notes_cli.py::test_note_import_markdown
```

If your test targets a function such as [`run_update`](src/rekipedia/orchestrator/run_update.py#L27) or [`EmbedPipeline.update`](src/rekipedia/rag/embedder.py#L733), it is often worth starting with a single scenario and then broadening to the whole file.

> **Sources:** `tests/test_notes_cli.py` · `tests/test_notes_store.py` · `tests/test_notes_server.py` · `tests/test_notes_rag.py` · `tests/test_rag.py` · `tests/test_update.py` · `src/rekipedia/orchestrator/run_update.py` · L27–L244 · [`run_update`](src/rekipedia/orchestrator/run_update.py#L27) · `src/rekipedia/rag/embedder.py` · L477–L892 · [`EmbedPipeline.build`](src/rekipedia/rag/embedder.py#L477) · [`EmbedPipeline.update`](src/rekipedia/rag/embedder.py#L733)

## CI/CD

No CI configuration files were present in the analysis evidence (`ci_files` is empty), so there is **no observable CI/CD pipeline to document** from the repository snapshot.

What we can say from the available evidence:

- The project has a standard Python packaging/test setup
- The test command is `pytest`
- The build command is `uv build`
- The package exposes CLI entry points [`rekipedia = "rekipedia.cli:main"` and `reki = "rekipedia.cli:main"`](README.md)

In other words, automated validation is clearly intended, but the concrete CI provider, workflow steps, and triggers are not visible in the current repository evidence.

> **Sources:** `ci_files` empty in analysis data · `pytest` test command from analysis data · `uv build` build command from analysis data · `README.md` entry points for [`rekipedia.cli:main`](README.md)