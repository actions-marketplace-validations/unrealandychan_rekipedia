# Release Notes

## v0.9.12 — Agent File Injection & CI/CD Hardening

### What's new

#### `reki init` auto-writes AI agent instruction files
- `reki init .` now writes three agent instruction files automatically:
  - `CLAUDE.md` — Claude Code integration with full `reki` command reference
  - `AGENTS.md` — Codex / OpenAI Agents integration
  - `.github/copilot-instructions.md` — GitHub Copilot instructions
- Each file contains: command table, when-to-use rules, first-time setup, litellm provider reference
- Skip with `--no-agent-files` flag if not needed
- AI coding tools in any rekipedia-initialised project will automatically know how to use `reki`

#### CI/CD hardening
- goreleaser ldflags now correctly point to `github.com/unrealandychan/rekipedia/cmd/rekipedia/cmd.*` — `reki --version` now shows the real version in releases (was always showing `dev`)
- `go-ci.yml`: Go 1.24, CGO_ENABLED=0, removed stale branch triggers
- `go-release.yml`: `if: success()` guard, `HOMEBREW_TAP_TOKEN` passed via env var (not CLI arg)
- `update-homebrew-tap.py`: reads PAT from `os.environ["HOMEBREW_TAP_TOKEN"]`; Formula now correctly installs `reki` binary

#### New workflows
- `.github/workflows/npm-publish.yml` — tag-triggered npm publish using `NPM_TOKEN` secret
- `.github/workflows/python-ci.yml` — Python 3.11 + 3.12 matrix CI with wheel smoke test

#### Other
- `LICENSE` — MIT License added
- `package.json` — placeholder `your-org` URLs replaced with real repo URLs

### Tests
- 11/11 Go packages passing ✅

---

## v0.9.11 — Rebrand: rekipedia + reki CLI

### What's new

#### Full rebrand from `close-wiki` → `rekipedia`
- CLI binary renamed: `rekipedia` (full) + `reki` (short alias)
- PyPI package: `rekipedia`
- npm package: `rekipedia`
- Homebrew Formula: `brew tap unrealandychan/tap && brew install rekipedia`
- All internal imports, config paths (`.rekipedia/`), env vars (`REKIPEDIA_*`) updated
- Landing page: https://unrealandychan.github.io/rekipedia-releases/

#### Go rewrite (feat/golang-rewrite → main)
- Go binary supports: `init`, `scan`, `update`, `ask`, `serve`, `embed`, `export`
- Zero Python dependency for Go binary (distributed via Homebrew)
- Full Python package retains RAG / FAISS support

#### `reki init` improvements
- Creates `.rekipedia/config.yml` scaffold
- Updates `.gitignore` with store.db, agent files
- `ensureGitIgnore` now actually writes the file (was silent no-op)

---

## v0.8.0 — Multi-language Support & Performance

### What's new

#### Extended language support
- Added Go, Rust, Java, C/C++ symbol extraction
- Language auto-detection from file extensions
- `languages` config key to restrict scanning scope

#### Performance improvements
- Parallel file processing with configurable worker count
- Incremental hash-based change detection (skip unchanged files)
- SQLite WAL mode for concurrent read access during `reki serve`

#### Web UI (`reki serve`) enhancements
- Full-text search across all wiki pages
- Side-by-side source view with syntax highlighting
- Dark/light theme toggle

### Tests
- 108/108 Python tests passing ✅

---

## v0.7.3 — is_implementation Heuristic in Planner & Token-Aware File Skip

### What's new

#### `is_implementation` heuristic in planning summary
- `_build_planning_summary()` now counts `impl_file_count`, `test_file_count`, and `config_file_count` using the same path-based heuristic as the RAG embedder
- These counts are included in the planner JSON payload sent to the LLM — enables more precise wiki structure decisions:
  - High `impl_file_count` → more core-component pages
  - `test_file_count < 3` → skip dedicated testing page
  - `config_file_count < 2` → skip configuration page
- The planner system prompt now references these fields in its page-splitting rules

#### Token-aware file skip (env var configurable)
- `_MAX_CODE_CHARS` and `_MAX_DOC_CHARS` in `embedder.py` are now overridable via env vars:
  - `REKIPEDIA_MAX_CODE_CHARS` (default: 320000 = ~80K tokens)
  - `REKIPEDIA_MAX_DOC_CHARS` (default: 32000 = ~8K tokens)
- Embedder now explicitly pre-checks file size before chunking and logs skipped files
- Progress callback reports skipped-too-large count: `"Embedding 42 chunks from 8 files (2 files skipped — too large)…"`

### Tests
- 108/108 passing ✅

---

## v0.7.1 — Page Importance, Wiki Export & Embed Provider Selection

### What's new

**v0.7.1** rounds out the RAG foundation with three user-facing improvements.

#### Page importance scoring
- `PlannerAgent` now generates an `importance` score (0–100) for every wiki page alongside the existing `priority` field
- `WikiPlan.nav_order` is sorted by `priority` descending — most critical pages appear first in the sidebar
- Importance is stored in `manifest.json` under `pages_meta` for downstream tooling

#### Wiki export (`rekipedia export`)
- New `rekipedia export [REPO]` command bundles the entire wiki into a portable file
- Three formats via `--format`:
  - `md` — single combined Markdown document with page headers (default)
  - `zip` — archive with one `.md` per page plus `manifest.json`
  - `json` — structured JSON with all pages, metadata, and importance scores
- `--output` flag controls the destination path

#### Embed provider selection
- `rekipedia scan` now accepts `--embed-model` and `--embed-provider` flags to configure the embedding model at scan time
- `rekipedia embed` gains a `--provider` flag
- Provider is stored in `LLMConfig.embed_provider` and passed to litellm as `{provider}/{model}` for routing
- Env vars: `REKIPEDIA_EMBED_MODEL`, `REKIPEDIA_EMBED_PROVIDER`
- Supports any litellm-compatible provider: `openai`, `ollama`, `azure`, `cohere`, etc.

### Tests
- 108/108 passing (19 new tests across importance, export, embed provider, LLM client retry, CLI coverage)
- Coverage: 74.7% (up from ~70%)

---

## v0.7.0 — RAG / FAISS Semantic Search & Hybrid Q&A

### What's new

**v0.7.0** adds a full RAG (Retrieval-Augmented Generation) pipeline powered by FAISS, enabling semantic search over source code chunks at Q&A time.

#### FAISS embed pipeline (`rekipedia embed`)
- New `rekipedia embed [REPO]` command builds a FAISS flat L2 index over chunked source files
- Chunks are ~1000 characters, stored in `.rekipedia/rag/chunks.json`; index saved to `.rekipedia/rag/index.faiss`
- Uses `litellm.embedding()` — model-agnostic, works with any litellm provider

#### Hybrid Q&A retrieval
- `rekipedia ask` now uses **hybrid retrieval**: FAISS top-8 code chunks + all wiki pages
- Code chunks are injected as additional context under `## Relevant Source Code` in the LLM system prompt
- Falls back gracefully to wiki-only mode when no FAISS index exists

#### Auto-embed on scan
- If `REKIPEDIA_EMBED_MODEL` is set, `rekipedia scan` automatically builds the FAISS index after wiki generation (step 8)

#### scan_meta.json
- Each scan now writes `.rekipedia/scan_meta.json` recording: `model`, `timestamp`, `rekipedia_version`, `file_count`, `embedded` flag

### Tests
- 89/89 passing
- 8 new RAG tests (`tests/test_rag.py`)

---

## v0.6.0 — Agentic Wiki Orchestration & DeepWiki-Style Structure

### What's new

**v0.6.0** introduces a fully agentic wiki generation pipeline: a `PlannerAgent` dynamically designs the wiki structure before writing any pages, replacing the previous fixed 9-page layout.

#### PlannerAgent — dynamic wiki structure
- New `PlannerAgent` (`synthesis/planner.py`): one LLM call analyses the repo and decides the entire wiki structure — page count, titles, focus, nav order, and search tags
- Page count is now **dynamic**: 3 pages for a tiny CLI tool, 12+ for a large framework (was fixed at 9)
- **DeepWiki-style sections**: pages are grouped into logical sections (`getting-started`, `architecture`, `core-components`, `api-reference`, `development`, `ecosystem`) embedded in frontmatter for sidebar navigation
- `WikiPlan` object: `pages`, `sections`, `nav_order`, `index_slug` — stored in wiki evidence for web UI consumption
- Graceful fallback: if LLM planning fails, `_default_plan()` heuristically generates 3–6 pages based on what's detected

#### Context slicing per page
- `_slice_payload()`: each `PageAgent` only receives the data keys it declared in `required_data` (e.g. `testing` page gets `test_commands + symbols + files_seen`, NOT full relationships or class hierarchy)
- Payload built **once** and sliced N ways — eliminates N-fold redundant serialisation
- Result: ~40–60% reduction in tokens sent to LLM for non-architecture pages

#### Improved page focus instructions
- Planner writes detailed `focus` per page specifying: exact headings, required tables, which Mermaid diagrams, which symbols to cite
- New mandatory page: `repository-structure` for repos with ≥10 files — full annotated tree + directory table
- Page splitting rules: >5 major modules → one page per module; complex architecture → split into `architecture-overview` + `architecture-data-flow`

#### Navigation & searchability
- `nav_order` in wiki frontmatter: planner orders pages from conceptual overview → specific reference (new-developer-friendly reading order)
- `tags` in frontmatter: 2–4 tags per page from a controlled vocabulary (`overview`, `architecture`, `api`, `testing`, `configuration`, etc.)
- `section` in frontmatter: enables sidebar grouping in web UI

#### Agent skill for AI coding assistants
- New `rekipedia-agent-skill.md`: Hermes skill that teaches Copilot, Claude Code, Codex, and other AI agents how to use rekipedia to understand codebases without reading every file
- Covers: install, scan, ask, serve, update, direct wiki page reading, environment variables, common pitfalls

### Tests
- 69/70 passing (1 pre-existing `sqlite_utils` import failure)
- Updated hardcoded `== 9` page count assertions → `>= 3` (page count is now dynamic)

## v0.5.0 — Deep Wiki, Interactive Ask & Developer Experience

### What's new

**v0.5.0** is a major quality-of-life release covering four areas: richer wiki generation, a streaming interactive CLI, a local web UI, and developer tooling.

#### 9-page DeepWiki-style generation
- Wiki expanded from **5 fixed pages → 9 deep pages**: `index`, `architecture`, `core-modules`, `algorithms`, `cli-and-api`, `installation-and-setup`, `configuration`, `testing`, `ecosystem-and-integrations`
- Each page has a detailed per-page prompt specifying required sections, Mermaid diagrams, tables, and code examples (800–1200 words target)
- System prompt upgraded: LLM now outputs **rich Markdown** (not JSON), with mandatory `## Section` / `### Subsection` headings

#### Source citations (anti-hallucination)
- Every wiki page now includes **inline source links**: [`ClassName`](path/to/file.py#L12)
- Every `##` section ends with a `> **Sources:** ...` block citing real file paths and line numbers
- `symbol_index` (name → `{file, line_start, line_end, kind}`) is injected into the LLM payload for accurate lookups

#### Rich architecture diagram
- `DiagramBuilder` now generates `flowchart LR` with **labelled edges** (`-->|imports|`, `-.->|calls|`, `<|-- : inherits`)
- **Entry points highlighted in gold** (`fill:#f4a700`)
- Pre-built diagram is injected into the architecture page — LLM embeds it verbatim (no hallucinated graphs)

#### Interactive ask REPL with streaming
- `rekipedia ask` now starts an **interactive session** — ask unlimited questions until Ctrl+C
- Answers **stream token-by-token** to the terminal in real time
- **Rich spinner** (`⠋ Thinking…`) while waiting for the first token
- Single-shot backward-compat mode via `rekipedia ask -q "question"`

#### Web UI (`rekipedia serve`)
- New `rekipedia serve` command — starts a **FastAPI + Jinja2 local server** (default: `http://127.0.0.1:7070`)
- Dark-themed wiki browser: navigate all generated pages, view diagrams
- **Grounded Q&A in the browser**: ask questions, get answers from the same `run_ask` pipeline
- **Q&A history** stored in SQLite (`qa_history` table) and browsable in the UI
- Options: `--host`, `--port`, `--no-browser`, `--wiki-dir`

#### tqdm progress bars
- `rekipedia scan` now shows **two real-time progress bars**:
  - `🔍 Extracting shards: 2/5 [00:04<00:08, id=src/cli]`
  - `📝 Generating wiki pages: 4/9 [01:23<01:45, page=algorithms]`
- ETA visible for the longest step (wiki generation)

#### `--verbose` debug mode
- `rekipedia scan . --verbose` enables:
  - Full `litellm._turn_on_debug()` — HTTP requests, model responses
  - `httpx` debug logs
  - Per-step symbol/relationship counts
  - Rich traceback with local variables on error
- Normal mode shows `Tip: run with --verbose for full debug output` on error

#### `make release-all`
- New Makefile target: `make release-all PYPI_TOKEN=xxx NPM_TOKEN=xxx [VERSION=x.y.z]`
- 5-step pipeline: version bump → build → git tag + push → PyPI → npm

#### Bug fix: Docker sandbox argument order
- Fixed `DockerSandboxRunner` passing `python3 /app/analyze_shard.py` as ENTRYPOINT args (causing `Usage:` error on exit 1). Now correctly passes only the two file-path arguments.

### Tests
- 69/70 passing (1 pre-existing `sqlite_utils` import failure, unrelated to rekipedia deps)
- Updated hardcoded `== 5` page count assertions → `== 9`

### Upgrade notes
- Run `uv tool uninstall rekipedia && uv tool install git+https://github.com/unrealandychan/rekipedia` to get the M1-compatible arm64 binary
- No DB migration needed

---

## v0.4.0 — Phase 4: Grounded Q&A

### What's new

**Phase 4** brings `rekipedia ask` — the product's headline feature.

#### Ask command
- `rekipedia ask QUESTION` — answers your question grounded exclusively in the wiki pages and symbol index produced by the last scan.
- `--repo PATH` — target a different repository root.
- `--model`, `--output-dir`, `REKIPEDIA_MODEL` env var — same overrides as `scan`.

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

No migration needed. Requires a successful `rekipedia scan` before `ask` will work.

---

## v0.3.0 — Phase 3: Incremental Update

### What's new

**Phase 3** makes `rekipedia update` fast by only re-extracting changed files.

#### Update command
- `rekipedia update [REPO]` — fully implemented with `--no-docker`, `--output-dir`, `--model`.
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

**Phase 2** delivers the full `rekipedia scan` pipeline end-to-end.

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
- `rekipedia scan [REPO]` — fully implemented with:
  - `--no-docker` flag to force in-process extraction
  - `--output-dir PATH` to write output outside the repo
  - `--model`, `--api-key`, `--base-url` overrides
  - `REKIPEDIA_MODEL`, `REKIPEDIA_API_KEY`, `REKIPEDIA_BASE_URL` env var overrides
  - Rich progress display

#### Storage
- Phase 2 data stored in dedicated `scan_*` tables (`scan_runs`, `scan_snapshots`, `scan_files`, `scan_symbols`, `scan_relationships`, `scan_wiki_pages`, `scan_diagrams`) to avoid schema conflicts with Phase 1 tables.

### Output structure

```
.rekipedia/
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
- `rekipedia init [REPO]` — idempotent initialisation command. Creates `.rekipedia/config.yml` with LLM provider block and updates `.gitignore`.
- `rekipedia scan`, `rekipedia update`, `rekipedia ask` — registered as stubs; full implementation in Phases 2–4.

#### Core infrastructure
- **SQLite store** (`sqlite-utils`) with full 12-table schema: `repo_snapshot`, `files`, `symbols`, `relationships`, `pages`, `chunks`, `diagrams`, `qa_cache`, `runs`, `schema_version`, `generator_config`, `ignore_rules`, `content_hashes`.
- **LLM client** backed by [litellm](https://docs.litellm.ai) — supports OpenAI, Anthropic, Google Gemini, Ollama, and 100+ other providers via a single config block.
- **Snapshotter** — SHA-256 file walker with `pathspec` (`.gitignore`-style) ignore support.
- **Pydantic v2 contracts** — `AnalysisResult`, `Symbol`, `Relationship`, `Shard`, `FileManifest`, `LLMConfig`.
- **JSON Schema** for `AnalysisResult` (draft-07) for sandbox contract validation.

#### Packaging
- Python package `rekipedia` (PyPI) via `uv`/`pip`; entry point `rekipedia`.
- npm shim that delegates `npx rekipedia` → `uvx rekipedia` → `python -m rekipedia`.
- `Makefile` with `install`, `dev`, `test`, `lint`, `build`, `docker-build`, `release-pypi`, `release-npm`, `release`, `clean`.

### Upgrade notes

First release — no migration needed.

---

*Planned for Phase 3:* Incremental `rekipedia update` (diff-based rescans).
*Planned for Phase 4:* `rekipedia ask` — grounded Q&A from the knowledge store.
