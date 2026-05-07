---
slug: cli-and-api
title: "CLI Reference and Programmatic API"
section: general
pin: false
importance: 50
created_at: 2026-05-07T04:11:47Z
rekipedia_version: 0.10.9
---

# CLI Reference and Programmatic API

## Overview

This page documents the public command-line interface and the external-facing Python APIs that are clearly visible in the repository analysis. The primary entry point for the Python CLI is [`main`](src/rekipedia/cli/__init__.py#L26), which is exposed via the package entry points `rekipedia = "rekipedia.cli:main"` and `reki = "rekipedia.cli:main"` in the project metadata. The CLI is built with Click and dispatches into subcommands defined under `src/rekipedia/cli/`, including the notes management commands in [`rekipedia.cli.note`](src/rekipedia/cli/note.py#L1-L153) and the RAG embedding command in [`rekipedia.cli.embed`](src/rekipedia/cli/embed.py#L1-L201).

On the programmatic side, the main external APIs surfaced by the analysis are the orchestrator functions [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45-L433), [`run_update`](src/rekipedia/orchestrator/run_update.py#L27-L244), and [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L304-L349), plus the storage and RAG APIs [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39-L827) and [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443-L892).

> **Sources:** `src/rekipedia/cli/__init__.py` · L26–L27 · [`main`](src/rekipedia/cli/__init__.py#L26)  
> **Sources:** `src/rekipedia/cli/note.py` · L1–L153 · [`note_cmd`](src/rekipedia/cli/note.py#L27), [`note_add`](src/rekipedia/cli/note.py#L35), [`note_list`](src/rekipedia/cli/note.py#L49), [`note_remove`](src/rekipedia/cli/note.py#L70), [`note_edit`](src/rekipedia/cli/note.py#L96), [`note_import`](src/rekipedia/cli/note.py#L127)  
> **Sources:** `src/rekipedia/cli/embed.py` · L22–L201 · [`embed_cmd`](src/rekipedia/cli/embed.py#L85), [`_check_rag_deps`](src/rekipedia/cli/embed.py#L22)  
> **Sources:** `src/rekipedia/orchestrator/run_ask.py` · L304–L349 · [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L304), [`stream_ask`](src/rekipedia/orchestrator/run_ask.py#L333)  
> **Sources:** `src/rekipedia/orchestrator/run_digest.py` · L45–L433 · [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45)  
> **Sources:** `src/rekipedia/orchestrator/run_update.py` · L27–L244 · [`run_update`](src/rekipedia/orchestrator/run_update.py#L27)  
> **Sources:** `src/rekipedia/storage/sqlite_store.py` · L39–L827 · [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39)  
> **Sources:** `src/rekipedia/rag/embedder.py` · L443–L892 · [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443)

## CLI Reference

### `rekipedia` / `reki`

The top-level Click group is implemented by [`main`](src/rekipedia/cli/__init__.py#L26). The analysis shows it is decorated with a version option and acts as the umbrella entry point for all subcommands imported by `src/rekipedia/cli/__init__.py`.

Because the analysis does not include the exact Click option declarations for the root command, the observable behavior is limited to the existence of the group and version support.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--version` | flag | package version (`0.10.9`) | Display the CLI version and exit |

**Usage example**

```bash
rekipedia --version
```

> **Sources:** `src/rekipedia/cli/__init__.py` · L26–L27 · [`main`](src/rekipedia/cli/__init__.py#L26)

---

### `rekipedia note`

The notes command group is defined by [`note_cmd`](src/rekipedia/cli/note.py#L27). It exposes note lifecycle operations backed by [`_get_store`](src/rekipedia/cli/note.py#L16), which opens a [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39).

#### `rekipedia note add`

Implemented by [`note_add`](src/rekipedia/cli/note.py#L35). This command inserts a new tech lead note using [`SqliteStore.upsert_note`](src/rekipedia/storage/sqlite_store.py#L631).

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `content` | argument | required | Note body to store |
| `--tag` | option | none | Attach a note tag |

**Usage example**

```bash
rekipedia note add "Investigate caching behavior in the update pipeline" --tag followup
```

#### `rekipedia note list`

Implemented by [`note_list`](src/rekipedia/cli/note.py#L49). It loads notes through [`SqliteStore.list_notes`](src/rekipedia/storage/sqlite_store.py#L658) and can emit JSON.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--tag` | option | none | Filter notes by tag |
| `--json` | flag | `false` | Emit JSON instead of human-readable output |

**Usage example**

```bash
rekipedia note list --tag followup --json
```

#### `rekipedia note remove`

Implemented by [`note_remove`](src/rekipedia/cli/note.py#L70). It accepts an ID or ID prefix, searches notes via [`SqliteStore.list_notes`](src/rekipedia/storage/sqlite_store.py#L658), and deletes the matching row with [`SqliteStore.delete_note`](src/rekipedia/storage/sqlite_store.py#L687).

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `note_id` | argument | required | Note ID or prefix |

**Usage example**

```bash
rekipedia note remove 1a2b3c
```

#### `rekipedia note edit`

Implemented by [`note_edit`](src/rekipedia/cli/note.py#L96). It supports direct content replacement or interactive editing via `$EDITOR`, and persists via [`SqliteStore.upsert_note`](src/rekipedia/storage/sqlite_store.py#L631). The implementation uses a temporary file and external editor process.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `note_id` | argument | required | Note ID or prefix |
| `--content` | option | none | New content; if omitted, opens editor |

**Usage example**

```bash
rekipedia note edit 1a2b3c --content "Revised note text"
```

#### `rekipedia note import`

Implemented by [`note_import`](src/rekipedia/cli/note.py#L127). This command imports notes from a YAML or Markdown file through [`import_notes_from_file`](src/rekipedia/notes/__init__.py#L7).

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `file` | argument | required | Input file path |
| `--dry-run` | flag | `false` | Parse and report without writing notes |

**Usage example**

```bash
rekipedia note import ./notes.yml
```

> **Sources:** `src/rekipedia/cli/note.py` · L16–L153 · [`_get_store`](src/rekipedia/cli/note.py#L16), [`note_cmd`](src/rekipedia/cli/note.py#L27), [`note_add`](src/rekipedia/cli/note.py#L35), [`note_list`](src/rekipedia/cli/note.py#L49), [`note_remove`](src/rekipedia/cli/note.py#L70), [`note_edit`](src/rekipedia/cli/note.py#L96), [`note_import`](src/rekipedia/cli/note.py#L127)  
> **Sources:** `src/rekipedia/storage/sqlite_store.py` · L631–L693 · [`SqliteStore.upsert_note`](src/rekipedia/storage/sqlite_store.py#L631), [`SqliteStore.list_notes`](src/rekipedia/storage/sqlite_store.py#L658), [`SqliteStore.delete_note`](src/rekipedia/storage/sqlite_store.py#L687)  
> **Sources:** `src/rekipedia/notes/__init__.py` · L7–L80 · [`import_notes_from_file`](src/rekipedia/notes/__init__.py#L7), [`_import_yaml`](src/rekipedia/notes/__init__.py#L22), [`_import_markdown`](src/rekipedia/notes/__init__.py#L43)

---

### `rekipedia embed`

Implemented by [`embed_cmd`](src/rekipedia/cli/embed.py#L85). This command builds or refreshes the repository RAG index, validates optional RAG dependencies via [`_check_rag_deps`](src/rekipedia/cli/embed.py#L22), configures an [`LLMConfig`](src/rekipedia/models/contracts.py) instance, and delegates indexing to [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443).

The analysis does not provide the exact Click decorator parameter list for `embed_cmd`, but the function signature and call graph show the externally relevant arguments.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `repo_path` | argument | required | Repository root to embed |
| `--output-dir` | option | `.rekipedia/` under repo | Directory for index and metadata |
| `--model` | option | configured model | Embedding model name |
| `--provider` | option | configured provider | LLM/embedding provider |
| `--api-key` | option | none | API key for remote providers |
| `--base-url` | option | none | Custom LiteLLM API base URL |
| `--top-k` | option | implementation-defined | Number of chunks to retain/query |
| `--verbose` | flag | `false` | Enable verbose logging |

**Usage example**

```bash
rekipedia embed . --output-dir .rekipedia --top-k 8 --verbose
```

> **Sources:** `src/rekipedia/cli/embed.py` · L22–L201 · [`_check_rag_deps`](src/rekipedia/cli/embed.py#L22), [`embed_cmd`](src/rekipedia/cli/embed.py#L85)  
> **Sources:** `src/rekipedia/rag/embedder.py` · L443–L892 · [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443), [`EmbedPipeline.build`](src/rekipedia/rag/embedder.py#L477), [`EmbedPipeline.search`](src/rekipedia/rag/embedder.py#L610)

## Programmatic API

### `import_notes_from_file(path)`

Defined in [`rekipedia.notes.__init__`](src/rekipedia/notes/__init__.py#L7). It parses either YAML or Markdown and returns a list of note dictionaries.

- **Signature:** [`import_notes_from_file(path)`](src/rekipedia/notes/__init__.py#L7)
- **Parameters**
  
  | Parameter | Type | Description |
  |-----------|------|-------------|
  | `path` | path-like | Input file to parse |

- **Return value**
  
  A list of note dictionaries parsed from the file. The exact keys are inferred from the importer logic and CLI usage, but the analysis only confirms that it returns a list of dict-like note records.

**Example usage**

```python
from pathlib import Path
from rekipedia.notes import import_notes_from_file

notes = import_notes_from_file(Path("notes.md"))
for note in notes:
    print(note)
```

> **Sources:** `src/rekipedia/notes/__init__.py` · L7–L19 · [`import_notes_from_file`](src/rekipedia/notes/__init__.py#L7), [`_import_yaml`](src/rekipedia/notes/__init__.py#L22), [`_import_markdown`](src/rekipedia/notes/__init__.py#L43)

---

### `SqliteStore`

[`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39) is the primary persistence abstraction for Python code. It wraps a database connection and supports both explicit open/close usage and context-manager usage.

- **Signature:** class [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39)
- **Parameters**
  
  | Parameter | Type | Description |
  |-----------|------|-------------|
  | `path` | path-like | Database path, typically `.rekipedia/store.db` |

- **Return value**
  
  The class represents a persistent store object; methods generally return row counts, booleans, IDs, or plain dicts depending on the operation.

**Example usage**

```python
from pathlib import Path
from rekipedia.storage.sqlite_store import SqliteStore

with SqliteStore(Path(".rekipedia/store.db")) as store:
    store.upsert_note("Remember to refresh the index", ["ops"], source="cli", note_id=None)
```

#### `SqliteStore.open()`

- **Signature:** [`open(self)`](src/rekipedia/storage/sqlite_store.py#L64)
- **Parameters:** none
- **Return value:** opens the backing DB connection and applies migrations

#### `SqliteStore.close()`

- **Signature:** [`close(self)`](src/rekipedia/storage/sqlite_store.py#L69)
- **Parameters:** none
- **Return value:** closes the DB connection

#### `SqliteStore.upsert_note(content, tags, source, note_id)`

- **Signature:** [`upsert_note(self, content, tags, source, note_id)`](src/rekipedia/storage/sqlite_store.py#L631)
- **Parameters**
  
  | Parameter | Type | Description |
  |-----------|------|-------------|
  | `content` | string | Note body |
  | `tags` | list-like / serialized tags | Note tags |
  | `source` | string | Provenance/source label |
  | `note_id` | string or null | Existing note ID to update, or null to insert |

- **Return value:** the persisted note ID

#### `SqliteStore.list_notes(tags)`

- **Signature:** [`list_notes(self, tags)`](src/rekipedia/storage/sqlite_store.py#L658)
- **Parameters**
  
  | Parameter | Type | Description |
  |-----------|------|-------------|
  | `tags` | string or iterable | Filter selector; may be empty for all notes |

- **Return value:** list of note rows

#### `SqliteStore.delete_note(note_id)`

- **Signature:** [`delete_note(self, note_id)`](src/rekipedia/storage/sqlite_store.py#L687)
- **Parameters**
  
  | Parameter | Type | Description |
  |-----------|------|-------------|
  | `note_id` | string | ID of the note to delete |

- **Return value:** `True` if deleted, otherwise `False`

**Example usage**

```python
from pathlib import Path
from rekipedia.storage.sqlite_store import SqliteStore

store = SqliteStore(Path(".rekipedia/store.db"))
store.open()
try:
    notes = store.list_notes(tags=None)
    print(notes)
finally:
    store.close()
```

> **Sources:** `src/rekipedia/storage/sqlite_store.py` · L39–L827 · [`SqliteStore`](src/rekipedia/storage/sqlite_store.py#L39), [`SqliteStore.open`](src/rekipedia/storage/sqlite_store.py#L64), [`SqliteStore.close`](src/rekipedia/storage/sqlite_store.py#L69), [`SqliteStore.upsert_note`](src/rekipedia/storage/sqlite_store.py#L631), [`SqliteStore.list_notes`](src/rekipedia/storage/sqlite_store.py#L658), [`SqliteStore.delete_note`](src/rekipedia/storage/sqlite_store.py#L687)

---

### `EmbedPipeline`

[`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443) builds and queries a FAISS index over repository source files. It is the core reusable RAG abstraction behind the CLI embed command and the incremental update path.

- **Signature:** class [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443)
- **Parameters**
  
  | Parameter | Type | Description |
  |-----------|------|-------------|
  | `output_dir` | path-like | Directory where `index.faiss`, chunk metadata, and model metadata are stored |
  | `llm_config` | `LLMConfig` | Embedding/LLM configuration |
  | `store` | `SqliteStore` or `None` | Optional DB handle for persisting chunk provenance |
  | `run_id` | string | Scan run identifier |

- **Return value**
  
  Instances expose `build`, `search`, `update`, `meta`, and `is_built`.

#### `EmbedPipeline.build(repo_root, progress_cb)`

- **Signature:** [`build(self, repo_root, progress_cb)`](src/rekipedia/rag/embedder.py#L477)
- **Parameters**
  
  | Parameter | Type | Description |
  |-----------|------|-------------|
  | `repo_root` | path-like | Repository root to index |
  | `progress_cb` | callable or null | Status callback |

- **Return value:** number of chunks embedded

#### `EmbedPipeline.search(query, top_k, mmr)`

- **Signature:** [`search(self, query, top_k, mmr)`](src/rekipedia/rag/embedder.py#L610)
- **Parameters**
  
  | Parameter | Type | Description |
  |-----------|------|-------------|
  | `query` | string | Search query |
  | `top_k` | int | Number of results requested |
  | `mmr` | bool | Whether to apply Maximal Marginal Relevance diversification |

- **Return value:** list of chunk result dictionaries

#### `EmbedPipeline.update(repo_root, changed_files, last_run_id, new_run_id, progress_cb)`

- **Signature:** [`update(self, repo_root, changed_files, last_run_id, new_run_id, progress_cb)`](src/rekipedia/rag/embedder.py#L733)
- **Parameters**
  
  | Parameter | Type | Description |
  |-----------|------|-------------|
  | `repo_root` | path-like | Repository root |
  | `changed_files` | list/path set | Paths that changed since the prior run |
  | `last_run_id` | string | Previous successful run ID |
  | `new_run_id` | string | New scan run ID |
  | `progress_cb` | callable or null | Status callback |

- **Return value:** number of chunks re-embedded

**Example usage**

```python
from pathlib import Path
from rekipedia.rag.embedder import EmbedPipeline
from rekipedia.storage.sqlite_store import SqliteStore
from rekipedia.models.contracts import LLMConfig

store = SqliteStore(Path(".rekipedia/store.db"))
store.open()
try:
    pipeline = EmbedPipeline(Path(".rekipedia"), LLMConfig(), store=store, run_id="scan-123")
    count = pipeline.build(Path("."), progress_cb=None)
    print("Embedded chunks:", count)
finally:
    store.close()
```

> **Sources:** `src/rekipedia/rag/embedder.py` · L443–L892 · [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443), [`EmbedPipeline.__init__`](src/rekipedia/rag/embedder.py#L446), [`EmbedPipeline.build`](src/rekipedia/rag/embedder.py#L477), [`EmbedPipeline.search`](src/rekipedia/rag/embedder.py#L610), [`EmbedPipeline.update`](src/rekipedia/rag/embedder.py#L733)

---

### `run_ask(question, repo_root, output_dir, llm_config, history)`

[`run_ask`](src/rekipedia/orchestrator/run_ask.py#L304) answers a question grounded in the repository knowledge store.

- **Signature:** [`run_ask(question, repo_root, output_dir, llm_config, history)`](src/rekipedia/orchestrator/run_ask.py#L304)
- **Parameters**
  
  | Parameter | Type | Description |
  |-----------|------|-------------|
  | `question` | string | User question |
  | `repo_root` | path-like | Repository root |
  | `output_dir` | path-like | `.rekipedia/` directory containing DB and wiki |
  | `llm_config` | `LLMConfig` | LLM settings |
  | `history` | list of turns | Prior conversation messages |

- **Return value:** Markdown string answer
- **Raises:** `RuntimeError` if no successful scan exists

**Example usage**

```python
from pathlib import Path
from rekipedia.orchestrator.run_ask import run_ask
from rekipedia.models.contracts import LLMConfig

answer = run_ask(
    "How does note import work?",
    repo_root=Path("."),
    output_dir=Path(".rekipedia"),
    llm_config=LLMConfig(),
    history=[],
)
print(answer)
```

#### `stream_ask(question, repo_root, output_dir, llm_config, history)`

- **Signature:** [`stream_ask(question, repo_root, output_dir, llm_config, history)`](src/rekipedia/orchestrator/run_ask.py#L333)
- **Parameters:** same as `run_ask`
- **Return value:** streamed token/chunk iterator
- **Notes:** same grounding/context assembly as `run_ask`, but streams the final model response

> **Sources:** `src/rekipedia/orchestrator/run_ask.py` · L304–L349 · [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L304), [`stream_ask`](src/rekipedia/orchestrator/run_ask.py#L333)

---

### `run_digest(repo_root, output_dir, llm_config)`

[`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45) performs the full scan pipeline: repository snapshotting, analysis, wiki synthesis, diagram generation, exports, and RAG index build. The docstring notes additional runtime controls such as `force_local`, `verbose`, `progress`, `languages`, `no_llm`, and `stdout_refactor`, but the symbol index exposes the exported callable as the three-argument function below.

- **Signature:** [`run_digest(repo_root, output_dir, llm_config)`](src/rekipedia/orchestrator/run_digest.py#L45)
- **Parameters**
  
  | Parameter | Type | Description |
  |-----------|------|-------------|
  | `repo_root` | path-like | Repository root to scan |
  | `output_dir` | path-like | `.rekipedia/` output directory |
  | `llm_config` | `LLMConfig` | LLM settings |

- **Return value:** not explicitly documented in the analysis; it persists results to storage and output files

**Example usage**

```python
from pathlib import Path
from rekipedia.orchestrator.run_digest import run_digest
from rekipedia.models.contracts import LLMConfig

run_digest(Path("."), Path(".rekipedia"), LLMConfig())
```

> **Sources:** `src/rekipedia/orchestrator/run_digest.py` · L45–L433 · [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45)

---

### `run_update(repo_root, output_dir, llm_config)`

[`run_update`](src/rekipedia/orchestrator/run_update.py#L27) performs incremental rescan and resynthesis. The docstring states it re-extracts only changed files, reuses unchanged symbols/relationships, and regenerates wiki pages with the combined symbol index.

- **Signature:** [`run_update(repo_root, output_dir, llm_config)`](src/rekipedia/orchestrator/run_update.py#L27)
- **Parameters**
  
  | Parameter | Type | Description |
  |-----------|------|-------------|
  | `repo_root` | path-like | Repository root |
  | `output_dir` | path-like | `.rekipedia/` output directory |
  | `llm_config` | `LLMConfig` | LLM settings |

- **Return value:** not explicitly documented in the analysis; it updates the existing run state and outputs
- **Notes:** may fall back to [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45) if no prior successful scan exists

**Example usage**

```python
from pathlib import Path
from rekipedia.orchestrator.run_update import run_update
from rekipedia.models.contracts import LLMConfig

run_update(Path("."), Path(".rekipedia"), LLMConfig())
```

> **Sources:** `src/rekipedia/orchestrator/run_update.py` · L27–L244 · [`run_update`](src/rekipedia/orchestrator/run_update.py#L27)

## Integration Examples

### Typical end-to-end workflow: scan, enrich, ask

A realistic workflow uses the CLI and programmatic APIs together:

1. Run a full scan with the CLI to create the store, wiki pages, and index.
2. Add tech lead notes through the CLI or via the store API.
3. Ask questions from Python using [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L304), which automatically incorporates the stored wiki pages, symbol snippets, RAG chunks, and notes.
4. When the repository changes, use [`run_update`](src/rekipedia/orchestrator/run_update.py#L27) to do an incremental refresh rather than rebuilding from scratch.

```bash
rekipedia embed . --output-dir .rekipedia
rekipedia note add "Remember to review the incremental update path" --tag ops
```

```python
from pathlib import Path
from rekipedia.orchestrator.run_ask import run_ask
from rekipedia.storage.sqlite_store import SqliteStore
from rekipedia.models.contracts import LLMConfig

repo_root = Path(".")
output_dir = Path(".rekipedia")

# Add a note programmatically
with SqliteStore(output_dir / "store.db") as store:
    store.upsert_note(
        content="Check whether page source attribution survives updates",
        tags=["ops"],
        source="api",
        note_id=None,
    )

# Ask a grounded question
answer = run_ask(
    "What changes when only one source file changes?",
    repo_root=repo_root,
    output_dir=output_dir,
    llm_config=LLMConfig(),
    history=[],
)
print(answer)
```

### Notes import pipeline: file → CLI → store

If notes are maintained in a Markdown or YAML file, the import path is:

- parse with [`import_notes_from_file`](src/rekipedia/notes/__init__.py#L7)
- persist through [`SqliteStore.upsert_note`](src/rekipedia/storage/sqlite_store.py#L631)
- verify with `rekipedia note list`

```python
from pathlib import Path
from rekipedia.notes import import_notes_from_file
from rekipedia.storage.sqlite_store import SqliteStore

notes = import_notes_from_file(Path("tech-notes.md"))
with SqliteStore(Path(".rekipedia/store.db")) as store:
    for note in notes:
        store.upsert_note(
            content=note["content"],
            tags=note.get("tags", []),
            source="import",
            note_id=note.get("id"),
        )
```

### RAG-first workflow: build index, then query

The embedding CLI and `EmbedPipeline` class can be combined directly if you need a custom pipeline around the stored index.

```python
from pathlib import Path
from rekipedia.rag.embedder import EmbedPipeline
from rekipedia.storage.sqlite_store import SqliteStore
from rekipedia.models.contracts import LLMConfig

output_dir = Path(".rekipedia")
with SqliteStore(output_dir / "store.db") as store:
    pipeline = EmbedPipeline(output_dir, LLMConfig(), store=store, run_id="custom-run")
    pipeline.build(Path("."), progress_cb=lambda msg: print(msg))
    chunks = pipeline.search("incremental update", top_k=5, mmr=True)
    for chunk in chunks:
        print(chunk["file"], chunk["score"])
```

### Workflow summary

| Step | CLI | API |
|------|-----|-----|
| Initial indexing | `rekipedia embed` | [`EmbedPipeline.build`](src/rekipedia/rag/embedder.py#L477) |
| Add a note | `rekipedia note add` | [`SqliteStore.upsert_note`](src/rekipedia/storage/sqlite_store.py#L631) |
| Import notes | `rekipedia note import` | [`import_notes_from_file`](src/rekipedia/notes/__init__.py#L7) |
| Ask a question | not shown in this task’s CLI slice | [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L304) |
| Incremental refresh | not shown in this task’s CLI slice | [`run_update`](src/rekipedia/orchestrator/run_update.py#L27) |

> **Sources:** `src/rekipedia/cli/embed.py` · L85–L201 · [`embed_cmd`](src/rekipedia/cli/embed.py#L85)  
> **Sources:** `src/rekipedia/cli/note.py` · L35–L153 · [`note_add`](src/rekipedia/cli/note.py#L35), [`note_import`](src/rekipedia/cli/note.py#L127)  
> **Sources:** `src/rekipedia/notes/__init__.py` · L7–L80 · [`import_notes_from_file`](src/rekipedia/notes/__init__.py#L7)  
> **Sources:** `src/rekipedia/rag/embedder.py` · L443–L892 · [`EmbedPipeline`](src/rekipedia/rag/embedder.py#L443)  
> **Sources:** `src/rekipedia/orchestrator/run_ask.py` · L304–L349 · [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L304)  
> **Sources:** `src/rekipedia/orchestrator/run_update.py` · L27–L244 · [`run_update`](src/rekipedia/orchestrator/run_update.py#L27)