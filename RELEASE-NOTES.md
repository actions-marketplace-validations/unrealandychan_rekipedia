# Release Notes

## v0.4.0 — Phase 4: Grounded Q&A

### What's new

**Phase 4** brings `close-wiki ask` — the product's headline feature.

#### Ask command
- `close-wiki ask QUESTION` — answers your question grounded exclusively in the wiki pages and symbol index produced by the last scan.
- `--repo PATH` — target a different repository root.
- `--model`, `--output-dir`, `CLOSE_WIKI_MODEL` env var — same overrides as `scan`.

#### Context assembly (`run_ask`)
- Loads all wiki pages from `wiki/*.md` (most informative for prose questions).
- Loads `exports/symbols.json` (symbol name, kind, file, signature).
- Assembles a context string within a 96 K-character budget (≈ 24 K tokens), truncating gracefully when needed.
- Passes context + a strict "cite your sources" system prompt to the LLM.

#### Grounding prompt (`ask_system.md`)
- Instructs the LLM to cite the source page or symbol for each claim.
- Explicitly prohibits inventing information not present in the context.
- Answers render as rich Markdown in the terminal (via `rich.markdown`).

#### Tests
- `tests/test_ask.py` — 5 tests covering return type, context inclusion, symbol index, and error paths (no store / no successful run).

### Upgrade notes

No migration needed. Requires a successful `close-wiki scan` before `ask` will work.

---

## v0.3.0 — Phase 3: Incremental Update

### What's new

**Phase 3** makes `close-wiki update` fast by only re-extracting changed files.

#### Update command
- `close-wiki update [REPO]` — fully implemented with `--no-docker`, `--output-dir`, `--model`.
- Falls back to a full `scan` automatically if no prior successful run exists.
- Reports "No changes detected" and exits early if all file hashes match.

#### Incremental pipeline (`run_update`)
- **Diff**: snapshot current files, compare SHA-256 hashes against the last run's `scan_files` table.
- **Carry-forward**: copies symbols and relationships for unchanged files from the previous run via raw SQL — zero re-extraction cost.
- **Re-extract**: only plans and runs shards for changed/new files.
- **Re-synthesise**: always does a full wiki page synthesis (all 5 pages) since the combined symbol index changes.
- **New run record**: each update creates a new `scan_runs` row, preserving full audit history.

#### Storage additions (`SqliteStore`)
- `get_latest_run_id(repo_path)` — finds the last successful run for a given repo.
- `get_files_for_run(run_id)` — returns stored file hashes for diff computation.
- `copy_unchanged_symbols(from_run_id, to_run_id, exclude_paths)` — bulk symbol carry-forward.
- `copy_unchanged_relationships(from_run_id, to_run_id, exclude_paths)` — bulk relationship carry-forward.

#### Bug fix: SQLite autocommit
- Switched `SqliteStore` to open connections with `isolation_level=None` (autocommit). Previously, `update_run_status(..., "success")` could be rolled back if the connection was closed before Python's sqlite3 committed the implicit transaction. This fix ensures run status is always durable.

#### Tests
- `tests/test_update.py` — 5 tests: fallback-to-full-scan, early-exit-on-no-changes, new-run-on-change, carry-forward symbols, wiki pages refreshed.

### Upgrade notes

No migration needed. The new helpers use existing `scan_*` tables.

---

## v0.2.0 — Phase 2: Repository Analysis & Wiki Generation

### What's new

**Phase 2** delivers the full `close-wiki scan` pipeline end-to-end.

#### Extractors (static analysis)
- **Python extractor** — AST-based extraction of functions, classes, docstrings, imports, inheritance chains, and entry points (`__main__` blocks).
- **TypeScript / JavaScript extractor** — Regex-based extraction of exported functions, arrow functions, classes, interfaces, types, and import relationships. Covers `.ts`, `.tsx`, `.js`.
- **Config extractor** — Parses `package.json`, `pyproject.toml`, `Dockerfile`, and CI YAML for build/test commands, dependencies, and deployment risks.

#### Orchestrator
- **Shard planner** (`ShardPlanner`) — Groups files by top-level directory and splits on a configurable token budget (default 12 000 tokens) to keep each LLM call within context limits.
- **`run_digest()` pipeline** — Snapshot → shard → extract → persist → synthesise → export. Full `try/finally` status tracking per run.

#### Sandbox runner
- **`DockerSandboxRunner`** — Runs extractors inside `Dockerfile.sandbox` (`python:3.12-slim`, `--network none`, read-only repo mount). Static analysis never touches the network.
- **`LocalRunner`** — In-process fallback, used automatically when Docker is unavailable or when `--no-docker` is passed.

#### Synthesis
- **`PageBuilder`** — LLM-driven generation of 5 canonical wiki pages: `index`, `architecture`, `core-modules`, `build-and-deploy`, `testing-strategy`. Respects `pin: true` frontmatter, `prompt_overrides`, and `exclude_pages` from config.
- **`DiagramBuilder`** — Generates Mermaid `flowchart TD` (module graph) and `classDiagram` (class hierarchy) directly from extracted relationship data.

#### Exporters
- **`MarkdownExporter`** — Writes wiki pages to `wiki/*.md` and diagrams to `diagrams/*.md`. Pinned pages are never overwritten.
- **`JsonExporter`** — Writes `exports/symbols.json`, `exports/relationships.json`, and `exports/manifest.json` (run summary with file count, symbol count, page list, diagram names).

#### CLI
- `close-wiki scan [REPO]` — fully implemented with:
  - `--no-docker` flag to force in-process extraction
  - `--output-dir PATH` to write output outside the repo
  - `--model`, `--api-key`, `--base-url` overrides
  - `CLOSE_WIKI_MODEL`, `CLOSE_WIKI_API_KEY`, `CLOSE_WIKI_BASE_URL` env var overrides
  - Rich progress display

#### Storage
- Phase 2 data stored in dedicated `scan_*` tables (`scan_runs`, `scan_snapshots`, `scan_files`, `scan_symbols`, `scan_relationships`, `scan_wiki_pages`, `scan_diagrams`) to avoid schema conflicts with Phase 1 tables.

### Output structure

```
.close-wiki/
├── store.db
├── wiki/
│   ├── index.md
│   ├── architecture.md
│   ├── core-modules.md
│   ├── build-and-deploy.md
│   └── testing-strategy.md
├── diagrams/
│   ├── module-graph.md
│   └── class-hierarchy.md
└── exports/
    ├── symbols.json
    ├── relationships.json
    └── manifest.json
```

### Upgrade notes

No migration needed for Phase 1 users. The new `scan_*` tables are created automatically on first scan.

---

## v0.1.0 — Phase 1: Foundation

### What's new

**Phase 1** establishes the full project skeleton, packaging, and core infrastructure.

#### CLI scaffold
- `close-wiki init [REPO]` — idempotent initialisation command. Creates `.close-wiki/config.yml` with LLM provider block and updates `.gitignore`.
- `close-wiki scan`, `close-wiki update`, `close-wiki ask` — registered as stubs; full implementation in Phases 2–4.

#### Core infrastructure
- **SQLite store** (`sqlite-utils`) with full 12-table schema: `repo_snapshot`, `files`, `symbols`, `relationships`, `pages`, `chunks`, `diagrams`, `qa_cache`, `runs`, `schema_version`, `generator_config`, `ignore_rules`, `content_hashes`.
- **LLM client** backed by [litellm](https://docs.litellm.ai) — supports OpenAI, Anthropic, Google Gemini, Ollama, and 100+ other providers via a single config block.
- **Snapshotter** — SHA-256 file walker with `pathspec` (`.gitignore`-style) ignore support.
- **Pydantic v2 contracts** — `AnalysisResult`, `Symbol`, `Relationship`, `Shard`, `FileManifest`, `LLMConfig`.
- **JSON Schema** for `AnalysisResult` (draft-07) for sandbox contract validation.

#### Packaging
- Python package `close-wiki` (PyPI) via `uv`/`pip`; entry point `close-wiki`.
- npm shim that delegates `npx close-wiki` → `uvx close-wiki` → `python -m close_wiki`.
- `Makefile` with `install`, `dev`, `test`, `lint`, `build`, `docker-build`, `release-pypi`, `release-npm`, `release`, `clean`.

### Upgrade notes

First release — no migration needed.

---

*Planned for Phase 3:* Incremental `close-wiki update` (diff-based rescans).
*Planned for Phase 4:* `close-wiki ask` — grounded Q&A from the knowledge store.
