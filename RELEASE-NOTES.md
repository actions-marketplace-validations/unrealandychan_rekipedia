## v0.12.0 — 2026-05-08

### Bug Fixes
- **Go shard ID overflow** — shard IDs no longer corrupt at idx≥10; switched from rune arithmetic to `fmt.Sprintf` (#86)
- **Token budget unified** — Python default raised 12K→40K to match Go; both now respect `REKIPEDIA_SHARD_TOKEN_BUDGET` env var (#87)
- **LLMClient.stream() dead code** — removed redundant api_key/base_url assignments already covered by `_base_kwargs()` (#89)
- **wiki_pages mtime cache** — `_wiki_pages()` now caches with directory mtime check instead of reading disk on every request (#90)
- **Frontmatter dedup** — `_summary_html()` now uses `_strip_yaml_frontmatter()` instead of inline duplicate logic (#91)
- **Go chunker cleanup** — removed unused `lines` param from `countLines`; eliminates wasted `strings.Split` allocation (#92)
- **Go embedder min() shadow** — removed local `min()` that shadowed Go 1.21+ builtin (#93)
- **Context priority unified** — Python and Go `run_ask` now assemble context in same order: RAG → notes → wiki → symbols (#97)

### Refactoring
- **run_ask/stream_ask** — shared preamble extracted into `_prepare_ask()` helper; eliminates code duplication (#88)

## v0.11.1 — 2026-05-08

### Bug Fixes
- **`/notes` page crash** — `notes_page` was using the old Starlette `TemplateResponse` API (`TemplateResponse("template", dict)`) while all other endpoints had already migrated to the new signature (`TemplateResponse(request, "template", ctx)`). Caused `TypeError: cannot use 'tuple' as a dict key` on Python 3.14 + new Starlette. Fixed to use `_ctx()` helper consistently.

## v0.11.0 — 2025-01-XX

### New Features
- **Codebase ToC Tree** (#85): scan now builds a `codebase_tree` table in SQLite with full directory/file hierarchy. Each node records path, name, kind (file/dir), language, parent reference, and depth. Lays groundwork for reasoning-based hierarchical retrieval (Phase 2).

### Go
- Added `models.TreeNode` struct
- Added `storage.UpsertTree()` and `storage.GetTree()` methods
- `RunDigest` now populates `codebase_tree` after snapshot

## v0.10.9 — 2026-xx-xx

### New Features
- **Symbol-boundary chunking** (`#78`): RAG chunks for Python, TypeScript, and Go files now align to AST symbol boundaries (functions, classes, methods) using tree-sitter. Chunks no longer cut through function definitions mid-statement, resulting in more semantically coherent RAG context. Falls back to character-based chunking when tree-sitter is unavailable or the language is unsupported.

## v0.10.8 — 2026-xx-xx

### New Features
- **Targeted wiki re-synthesis** (`#77`): `reki update` now tracks which source files contributed to each wiki page (`page_sources` table, migration 005). On update, only pages whose sources changed are re-synthesised. Unaffected pages are carried forward at zero LLM cost. Falls back to full re-synthesis if page sources not yet recorded (first update after upgrade).

## v0.10.7 — 2026-xx-xx

### New Features
- **Incremental embed on `reki update`** (`#76`): `reki update` now automatically refreshes the RAG index — only re-embedding chunks from changed files. Unchanged files carry forward their embeddings at zero API cost. New `EmbedPipeline.update()` method and `SqliteStore.carry_forward_rag_chunks()`. Expect ~90% fewer embedding API calls on typical updates.

## v0.10.6 — 2026-05-07

### New Features
- **Chunk-level provenance** (`#75`): RAG chunks now track `file_path`, `start_line`, `end_line`, `start_char`, `end_char`, and `text_hash` in `store.db`. New `rag_chunks` table (migration 004) and `SqliteStore` methods: `upsert_rag_chunks()`, `get_rag_chunks_by_file()`, `get_all_rag_chunks()`. Foundation for incremental re-embedding in #76.
- `EmbedPipeline` accepts optional `store` and `run_id` params — when provided, provenance is automatically persisted after each `reki embed` run.
- `_chunk_file()` now includes `start_line`, `end_line`, `end_char`, `text_hash` in every chunk dict.

## v0.10.5 — Tech Lead Notes

### New Features
- **Note storage** (#62): persistent `tech_lead_notes` table in SQLite, independent of scan runs
- **Note CLI** (#63): `reki note add/list/remove/edit/import` commands (Python + Go)
- **RAG injection** (#64): relevant notes auto-injected into `reki ask` context as high-priority team context
- **Batch import** (#65): `reki note import notes.yml` / `reki note import TECH_CONTEXT.md`
- **Web UI** (#66): `/notes` management page in `reki serve` with tag filtering and inline add/delete

# Release Notes

## v0.10.4 — Fix Docker Sandbox Missing tree-sitter Dependencies

### Bug Fix
- **Docker sandbox `ModuleNotFoundError`**: `Dockerfile.sandbox` was missing `tree-sitter`, `tree-sitter-go`, `tree-sitter-python`, `tree-sitter-typescript`, `tree-sitter-rust`, `tree-sitter-java` — Go shards (and others) would always fail inside the Docker sandbox.

---

## v0.10.3 — Wiki Generation Quality Improvements

### Improvements
- **Symbol sample sorted by importance**: Planner summary now shows `impl` files first, CI/test/config files last — LLM sees relevant source code, not GitHub Actions scripts.
- **File role classification**: Each symbol and relationship tagged with `file_role` (`impl`/`test`/`ci`/`config`/`doc`) in planner payload — LLM can filter noise.
- **Planner summary enhanced**: Includes `file_role_counts`, per-dir language breakdown, and multi-language instructions so LLM creates per-language pages for polyglot repos.
- **Architecture diagram improved**: Module graph now groups by top-level module (not individual symbols), filters external/stdlib packages, limits to top-20 modules by edge count — produces readable Mermaid diagrams.
- **Importance scores fixed**: Wiki pages now correctly inherit importance from planner spec (was always defaulting to 50).

---

## v0.9.38 — Refactor Analysis Pipeline

### New Features
- **`reki refactor` command** (Python + Go): Standalone command to detect code smells and generate `REFACTOR.md` + `refactor_report.json` without running a full scan.
- **Static analysis detectors** (Python + Go): Five detectors — `god_class`, `circular_dep`, `dead_code`, `large_file`, `high_coupling` — plus graph metrics: `high_fan_in`, `high_fan_out`, `deep_inheritance`.
- **LLM enrichment** (`--no-llm` to skip): Each detected issue gets an AI-generated problem statement, concrete refactoring suggestion, safest starting point, and risk level.
- **REFACTOR.md output**: Human/agent-readable Markdown guide grouped by severity (🔴 High / 🟡 Medium / 🟢 Quick Wins).
- **`refactor_report.json` output**: Machine-readable JSON report for CI/tooling integration.
- **`--with-refactor` flag on `reki scan`**: Auto-generate REFACTOR.md after scan completes.
- **`--stdout` flag**: Print REFACTOR.md to stdout for piping (`reki scan . --stdout | claude`).
- **`--no-llm` flag**: Run static analysis only, skip LLM enrichment.

### Internal
- New `refactor_types.go` — unified `RefactorIssue` struct (single source of truth across detector, enricher, writer).
- `Metrics` field unified to `map[string]any` across all Go refactor files.
- Python + Go feature parity: identical detectors, thresholds, severity levels, and output format.

---

## v0.9.37 — Go UI sync: sidebar search + section grouping

### Changes
- **Go `base.html` rewrite**: Full feature-parity with Python UI — sidebar now shows wiki pages grouped by `section` frontmatter field with collapsible category headers.
- **Search bar**: Live full-text search input at top of sidebar (250ms debounce), calls `/api/wiki/search`, shows title + snippet + section label. Escape to return to category view.
- **Design refresh**: Migrated to GitHub-style CSS variables (`--bg`, `--surface`, `--accent`, etc.) matching Python side exactly.

---

## v0.9.36 — Go sync: file-level graph + wiki full-text search

### Changes
- **Go `handleAPIGraph` rewrite**: Migrated to file-level dependency graph (nodes = source files, edges = import relationships). Matches Python v0.9.35 behaviour — `moduleCandidates()` resolves dotted module paths to `.py`/`.go`/`.ts`/`.js` file candidates.
- **Go `/api/wiki/search` (new)**: Full-text search across wiki page title, section, and body content. Returns slug, title, section, snippet, and title_match flag — feature-parity with Python v0.9.34.
- **`graphNode` struct**: Added `file` and `group` JSON fields for file-level graph display.

---

## v0.9.35 — Wiki Categories & Search

### New Features
- **Sidebar category grouping**: Wiki pages are now grouped by their `section` frontmatter field in the sidebar. Each group has a collapsible header — click to expand/collapse.
- **Live search filter**: Search box at the top of the wiki nav filters pages by title or section as you type. Matching groups auto-expand; empty groups are hidden.
- **Frontmatter `section` read by server**: `_wiki_pages()` now parses frontmatter YAML to extract both `title` and `section` fields, passing them to templates.

---

## v0.9.31 — Scan skip + Ask positional arg

### New Features
- **Scan skip-if-scanned** (Python + Go): `reki scan` skips if a `status='success'` run already exists in the DB. Use `--force`/`-f` to rescan.
- **`reki ask` positional arg**: `reki ask "your question"` now works directly without `-q` flag (Python + Go aligned).

---

## v0.9.30 — Frontmatter integrity fix

### Bug Fixes
- **`_ensure_frontmatter` always strips+rebuilds**: Prevents LLM hallucination garbage fields (e.g. `created_at: 0.9.23`) from surviving in wiki frontmatter.
- **`_strip_yaml_frontmatter` handles malformed FM**: Strips frontmatter even if closing `---` is missing; fallback to first blank line or `#` heading.

---

## v0.9.29 — Agent & MCP integration

### New Features
- **MCP `ask` tool** (#59): `reki mcp` now exposes an `ask` tool — agents can ask natural-language questions about the codebase grounded in wiki + RAG. Works with Claude Code, Cursor, and any MCP client.
- **Auto agent hint files** (#60): `reki scan` now auto-generates `CLAUDE.md`, `AGENTS.md`, and `.github/copilot-instructions.md` with instructions for AI agents to use `reki ask` and the MCP server.
- **Auto `.mcp.json`** (#61): `reki scan` auto-generates `.mcp.json` in the repo root for Claude Code MCP auto-discovery. Merges with existing entries; adds `.mcp.json` to `.gitignore`.

## v0.9.28 — Embed base URL isolation fix

### Bug Fixes
- **`embed_base_url` no longer falls back to `base_url`**: `reki embed` and `reki scan` previously used the LLM chat endpoint as the embedding base URL when `embed_base_url` was unset. This caused proxy misrouting. Both `embed.py` and `scan.py` now default to `""` (use provider default) unless `embed_base_url` / `REKIPEDIA_EMBED_BASE_URL` is explicitly set.

---

## v0.9.27 — Embedding refactor + test fixes

### Changes
- **Embedding via litellm unified path**: `_embed_batch` now always uses `litellm.embedding()` — `base_url` is passed as `api_base` parameter instead of raw httpx calls. Simpler, more reliable, supports all litellm providers consistently.
- **Tests updated**: `test_embed_batch_with_base_url` and `test_embed_batch_with_base_url_error` updated to mock litellm instead of httpx.

---

## v0.9.26 — Ask & Search Quality Improvements

### New Features
- **BM25 Symbol Search** (#52): `reki search` now uses BM25 scoring with camelCase/snake_case tokenization. Queries like `"entry point"` now find `main_entrypoint`. New `--kind` filter option. Go side updated with same tokenization logic.
- **Planner Keywords Field** (#54): Each generated wiki page now includes a `keywords: [...]` frontmatter field listing 5–10 exact symbol names and domain terms the page covers. Used by the ask pipeline for fast page routing.
- **Ask Page Relevance Ranking** (#53): `reki ask` now ranks wiki pages by query relevance (TF scoring + `keywords` frontmatter + `importance` boost) before context assembly. Prevents relevant pages from being pushed out of the token budget by alphabetically-prior irrelevant pages.
- **RAG MMR Deduplication** (#55): After FAISS top-K retrieval, Maximal Marginal Relevance (MMR) diversifies results. Near-duplicate chunks from the same function are de-prioritised, ensuring broader coverage. Opt-out via `REKIPEDIA_RAG_MMR=0`.
- **Silent Query Rewriting** (#56): `reki ask` silently rewrites natural-language questions to match codebase vocabulary before retrieval (e.g. `"how does login work"` → `"how does AuthService.authenticate / verify_credentials work"`). Opt-out via `--no-rewrite` or `REKIPEDIA_QUERY_REWRITE=0`.

---

## v0.9.25 — Graph Intelligence & Developer Tools

### New Features
- **Knowledge Gap Detection** (#43): Identifies untested hotspots — high call-count symbols with no test coverage. `knowledge_gaps` injected into wiki payload.
- **Graph Diff / Snapshot Comparison** (#44): `reki diff` compares two timestamped scan snapshots. Auto-saves snapshots in `.rekipedia/snapshots/`.
- **Hub & Bridge Node Detection** (#45): Degree-based centrality analysis. `hub_nodes` injected into wiki payload. Bridge nodes (high in+out degree) flagged.
- **Blast-Radius / Impact Analysis** (#46): `reki impact <file>` — BFS traversal shows all affected files, symbols, and tests for a changed file.
- **D3.js Interactive Graph** (#47): `/graph` route in `reki serve` — force-directed graph with edge filter, node search, section colour-coding.
- **MCP Server** (#48): `reki mcp` starts a JSON-RPC 2.0 MCP stdio server with 6 tools: get_context, search_nodes, get_relationships, get_knowledge_gaps, get_hub_nodes, get_impact.
- **Multi-Repo Watch Daemon** (#49): `reki watch add/start/list/remove` — background file watcher with debounced auto-indexing via `watchdog`.
- **Cross-Repo Search** (#50): `reki search <query> [--all-repos]` — parallel fan-out search across all registered repo DBs.
- **Graph Export** (#51): `reki export --format graphml|cypher|obsidian` — export to GraphML, Neo4j Cypher, and Obsidian wikilink vaults.

### Fixes
- Snapshot timestamp now uses microseconds to avoid collision when saving multiple snapshots in the same second.
- `tree-sitter-go`, `tree-sitter-java`, `tree-sitter-python`, `tree-sitter-typescript` installed in dev venv for full test suite.

---

## v0.9.24 — Fix Python CI: Add `_build_cross_module_summary` + slug/frontmatter hardening

### Fix: Python CI ImportError (`_build_cross_module_summary` missing)
- `tests/test_page_builder_relationships.py` imported `_build_cross_module_summary` from `page_builder` but the function did not exist in source
- Added `_build_cross_module_summary(relationships, symbols, files_seen)` — builds a per-module relationship map with `imports/imported_by`, `calls/called_by`, `inherits/inherited_by` keys; deduplicates edges; caps at 100 modules
- `_build_payload` now includes three new fields: `relationship_stats` (total + by_kind counts), `internal_relationships` (stdlib-filtered, capped at 800), `cross_module_summary`
- Increased `relationships` payload limit from 600 → 1500

### Fix: Slug sanitization + frontmatter hallucination stripping (Python & Go)
- `_sanitize_slug()` / `sanitizeSlug()` added to both sides — normalises LLM-generated slugs to `lowercase-hyphenated`, collapses runs, strips bad chars
- `_ensure_frontmatter()` (Python) now always strips and rebuilds frontmatter — eliminates hallucinated keys like `created_at`, `author`, `date`
- `ensureFrontmatter()` (Go) added — was completely missing; Go now matches Python behaviour
- Planner slug sanitization applied immediately after JSON parse on both sides

## v0.9.23 — Fix Go Release CI & Remove close-wiki Branding

### Fix: Go Release CI Homebrew tap 404
- `update-homebrew-tap.py` BASE_URL was pointing to `rekipedia-releases` repo → corrected to `rekipedia` main repo
- `.goreleaser.yaml` release target + brew url_template also updated to `rekipedia` repo

### Fix: Remove all `close-wiki` branding
- `base.html` sidebar title/subtitle: `close-wiki` → `rekipedia`
- `index.html` quick-start example: `close-wiki scan .` → `rekipedia scan .`
- All 4 occurrences removed (verified via grep)

---

## v0.9.22 — Mermaid Diagrams Now Render in Wiki Pages

### Mermaid.js rendering in wiki pages (Python + Go)
- All ` ```mermaid ` code blocks in wiki pages now **render as actual diagrams** instead of raw code
- Dark theme matching rekipedia's colour scheme (navy background, blue accent, gold highlights)
- HTML entity unescape fix: `markdown` library encodes `-->` as `--&gt;` — fixed before passing to Mermaid.js
- **"🕸 Open in Graph"** button appears on every `flowchart` / `classDiagram` — links to interactive D3 force graph
- **`{ }` toggle button** shows/hides raw Mermaid source for any diagram
- Render errors show inline with raw source fallback (no silent failures)

---

## v0.9.21 — Fix D3 Graph Edges Not Showing

### Fix: Graph API multi-strategy ID resolution (#graph-edges)
- **Root cause**: relationship `from_`/`to` names (e.g. `rekipedia.cli.scan`, `PageBuilder.build`) didn't match node IDs (format: `file::name`) → JS filter silently dropped all unresolved edges → only 6 edges visible for 1898 nodes
- **Fix**: replaced O(n) linear scan with O(1) dict lookup + 4-strategy resolver:
  1. Exact label match
  2. Already a valid node ID
  3. Dotted module name → last segment (`rekipedia.cli.scan` → `scan`)
  4. `Class.method` format → method name
- Self-loops dropped; edges capped at **2000** prioritised by kind (`inherits > calls > imports`)
- Response now includes `edge_count_total` field
- Go server applies same logic
- Added debug warning in graph.html for any remaining unresolved edges

---

## v0.9.20 — Richer Wiki Generation with Cross-Module Relationship Analysis

### Pre-computed cross-module summary in payload
- `_build_payload()` now pre-computes a `cross_module_summary` map grouping all internal `imports`, `calls`, and `inherits` relationships by module — top 100 most connected modules
- Added `relationship_stats` field `{total, by_kind}` so LLM knows relationship coverage
- Added `internal_relationships` field (stdlib-filtered, up to 800 internal edges)
- Relationship limit increased from 600 → **1500** (Python + Go)

### Stronger prompts for architecture and core-modules pages
- `architecture` page focus now requires: Cross-Module Dependency Map (Mermaid `flowchart LR` + table), Module Coupling Analysis (tightly coupled pairs, isolated modules, circular imports)
- `core-modules` page focus now requires per-module: Imports From, Imported By, Calls, Called By, Coupling Score — plus a summary cross-module table covering all documented modules

### digest_system.md — mandatory cross-module rules
- New "Cross-Module Relationship Rules" section: dependency table format, per-slug coverage rules, call chain tracing, coupling analysis
- LLM now required to use `cross_module_summary` data directly instead of inferring from raw edges

### Go page builder upgraded to match Python quality
- `pageSystemPrompt` rewritten with full Mermaid rules, source citation rules, cross-module rules
- Added `pageExtraFocus` entries for `architecture`, `core-modules`, `algorithms`, `cli-and-api` slugs
- Go `buildPayload()` relationship limit 200 → 1500, added `cross_module_summary` and `relationship_stats`

---

## v0.9.19 — Diagram & Relationship Bug Fixes

### Fix: diagram builder showing empty for all projects (#41)
- **Bug 1 — Storage layer**: `get_all_relationships()` returned raw SQLite tuples; `dict(row)` on a flat tuple raises `TypeError` which was silently caught, making every relationship an empty dict. Fixed with explicit column selection and named dict construction
- **Bug 2 — Go struct embedding**: Struct embedding (Go's form of composition/inheritance) was never extracted. Fixed by detecting `field_declaration` nodes without `field_identifier` and emitting `kind="inherits"` relationships for direct (`Animal`), pointer (`*Dog`), and cross-package (`pkg.Bar`) embedding
- **Go stdlib filter**: Added common Go stdlib packages (`fmt`, `strings`, `sync`, `net`, `context`, etc.) to external prefix filter in `diagram_builder.py` — previously shown as internal module relationships

---

## v0.9.18 — Knowledge Diff, D3 Graph Filter & Homebrew License Fix

### `reki diff` command — commit-level knowledge diff (#38)
- `rekipedia diff --from-ref HEAD~1 --to-ref HEAD` shows added/removed/changed symbols between commits
- Reads previous snapshot via `git show <ref>:.rekipedia/exports/symbols.json`
- Outputs diff in markdown or plain text format (`--format md|text`)
- Gracefully handles empty/missing stores (shows all current symbols as added)
- Both Python and Go implemented

### D3 graph search, filter & N-hop focus (#39)
- **Search/filter**: type in search box to filter nodes by name or file — non-matching nodes fade to 20% opacity
- **Group by file**: toggle button clusters and color-codes nodes by source file
- **N-hop focus**: click a node to highlight 1-hop neighbours; click again to expand to 2-hop; click background to reset
- All features preserve existing dark theme and gold god-node styling
- Both Python (FastAPI) and Go server templates updated

### Homebrew Formula license fix (#40)
- Fixed `license "Proprietary"` → `license :cannot_represent` (correct Ruby symbol for SPDX-incompatible licenses)
- Updated both `update-homebrew-tap.py` script and live `homebrew-tap/Formula/rekipedia.rb`

---

## v0.9.17 — Agent Context, Wiki Frontmatter & Scan Progress

### `reki context` command — agent-ready output (#35)
- `rekipedia context [REPO] --output context.md` generates a condensed single-file wiki for injection into coding agents
- `--max-tokens N` flag (default 32,000) truncates output to fit agent context windows
- Output includes YAML frontmatter + all wiki sections + top symbols
- Both Python and Go implemented

### YAML frontmatter for wiki pages (#36)
- Every generated `.rekipedia/wiki/*.md` page now includes YAML frontmatter:
  ```yaml
  ---
  title: Architecture Overview
  created_at: 2026-05-03T10:00:00Z
  rekipedia_version: 0.9.16
  importance: 95
  section: architecture
  tags: []
  pin: false
  ---
  ```
- Compatible with Obsidian, Jekyll, and CI automation
- Go `page_builder.go` updated with `ensureFrontmatter()` helper
- Existing frontmatter not duplicated on re-scan

### Scan progress display with ETA (#37)
- `reki scan` now shows Rich progress bars for both phases:
  - `🔍 Shard X/N` — extraction phase with ETA
  - `📝 Page X/N` — wiki synthesis phase with ETA
- Uses `rich.progress` with `SpinnerColumn`, `BarColumn`, `TimeRemainingColumn`
- Go orchestrator updated with pterm progress bar for page synthesis
- Existing `progress` callback still fires alongside visual display

### Tests
- **306 Python tests pass** | **Go: all 14 packages pass**
- 17 new tests: context cmd (7), wiki frontmatter (6), scan progress (4)

---



### Multi-language AST Extractors (#32)
- Added Go extractor using `tree-sitter-go` — extracts functions, structs, interfaces, imports; detects `func main()` entry point
- Added Rust extractor using `tree-sitter-rust` — extracts `fn`, `struct`, `trait`, `use`; `impl Foo for Bar` produces `uses` relationship
- Added Java extractor using `tree-sitter-java` — extracts classes, methods, imports; `extends` → `inherits`, `implements` → `uses`
- All three extractors registered in `ALL_EXTRACTORS` by file extension (`.go`, `.rs`, `.java`)
- 21 new tests (7 per extractor): symbol extraction, relationship detection, entry point, empty file handling

### Multi-turn Conversation Memory for `reki ask` (#33)
- `reki ask` REPL now maintains full conversation history across turns — follow-up questions have context
- History passed as `messages[]` to LLM (litellm multi-turn format)
- `--history-limit N` flag (default: 10 turns) — oldest turns dropped when limit exceeded
- `--no-save-session` flag to skip disk persistence
- Session auto-saved to `.rekipedia/sessions/<timestamp>.json` on exit
- Turn number shown in prompt: `[1] ❯`, `[2] ❯`, …
- 7 new tests covering history accumulation, limit truncation, session JSON persistence

### Go Binary Feature Parity (#34)
- `reki embed` — vector embedding pipeline in Go (chromem-go, no CGO)
- `reki export` — wiki bundle to markdown or JSON from SQLite store
- `reki update` — incremental re-scan (diff manifest vs current files, only re-process changed files)
- 10 new Go tests covering all three commands

### Test Fixes & CI Improvements
- Fixed `python-multipart` missing dependency (FastAPI Form support)
- Fixed `--cov=src/rekipedia` → `--cov=rekipedia` for installed wheel coverage tracking
- Fixed homebrew tap version strip (`${TAG#go/v}`) — was incorrectly building `vgo/v0.9.15` URLs
- Added `--skip=validate` to goreleaser for prefixed tag workflow
- Updated Homebrew Formula license: `"MIT"` → `"Proprietary"`
- Updated `README.md` license section: MIT → Proprietary & Confidential
- **289 Python tests pass** | **Go: all 14 packages pass**

---

## v0.9.14 — Phase 5 & 6: Graph UI + Extraction Quality

### Phase 5: Interactive Dependency Graph

#### `/graph` route with D3.js force-directed visualization (#27)
- `rekipedia serve` now exposes a `/graph` route rendering the full symbol dependency graph
- D3.js force-directed layout with dark theme and zoom/pan support
- God nodes (highest-degree symbols) highlighted with a distinct colour and larger radius

### Phase 6: Extraction Quality

#### Relationship confidence scoring (#28)
- Every extracted `Relationship` now carries a `confidence: float` (0.0–1.0) and an `evidence_tag: Literal["EXTRACTED", "INFERRED", "AMBIGUOUS"]`
- Default values are `1.0` / `"EXTRACTED"` so existing code is fully backward-compatible
- LLM-inferred edges receive `INFERRED`; ambiguous cross-shard edges receive `AMBIGUOUS`

#### Design rationale extraction (#29)
- Python extractor now collects `# NOTE:`, `# HACK:`, `# WHY:` (and `# IMPORTANT:`, `# TODO:`) inline comments
- Each comment is stored as a `RationaleNote` inside `AnalysisResult.rationale_notes`
- Rationale notes appear as lightweight knowledge nodes on the `/graph` route and in wiki pages

#### God nodes ranking (#30)
- `rekipedia.analysis.graph_analysis.compute_god_nodes()` computes in+out degree for every symbol
- Top-10 god nodes are surfaced in `index.md` under a **Key Symbols** section
- `/graph` highlights them for at-a-glance architectural understanding

#### Git hooks auto-rebuild (#31)
- `rekipedia hook install` writes a `post-commit` hook that runs `rekipedia update` in the background after every commit
- `rekipedia hook uninstall` removes only hooks managed by rekipedia (safe for pre-existing hooks)
- `rekipedia hook status` shows install state and last-modified timestamp

---

## v0.9.13 — Security Hardening, Testability & DX Improvements


### Security

#### Path traversal protection (#19)
- Go server: wiki slug validated against `^[a-zA-Z0-9_-]+$` before building filepath — rejects dots, slashes, and special characters with 404
- Python FastAPI server: same regex guard added to `/wiki/{slug}` handler

#### Go HTTP server timeouts (#20)
- `http.Server` now sets `ReadTimeout=15s`, `WriteTimeout=60s`, `IdleTimeout=120s`
- Prevents slow-loris DoS and resource exhaustion from idle connections

### Reliability

#### Real `/api/health` DB probe (#23)
- `/api/health` now opens and probes `store.db` instead of returning a static `{"status":"ok"}`
- Returns `{"status":"degraded","db":"error:..."}` + HTTP 503 when DB is unavailable
- Returns `{"status":"ok","db":"no_store"}` when no scan has been run yet
- Both Go and Python servers updated

### Testability

#### LLMCaller interface injection (#22)
- **Go**: `llm.Caller` interface (`Call` + `StreamCall`) extracted from `*llm.Client`
  - `llm.FakeCaller` test double with configurable `Response`/`StreamChunks`/`CallErr`
  - `AskOptions.Caller` + `DigestOptions.Caller` fields for injection
  - `synthesis.NewPlannerAgent` + `NewPageBuilder` now accept `llm.Caller` (was `*llm.Client`)
- **Python**: `LLMCaller` runtime-checkable `Protocol` with `call`/`stream` methods
  - `FakeCaller` test double
  - `PlannerAgent` + `PageBuilder` accept `caller=` keyword argument

### CI / CD

#### Python CI: pytest + coverage gate (#21, #25)
- Python CI now runs full `tests/` suite (was smoke test only)
- `--cov-fail-under=60` enforced — PRs that drop coverage below 60% fail CI
- Test deps (`pytest`, `pytest-asyncio`, `httpx`, `pytest-cov`) installed automatically
- `tests/` directory added to path trigger

#### Fix release tag namespace collision (#24)
- Go release workflow now triggers on `go/v*` tags (e.g. `go/v1.3.0`)
- Python release workflow now triggers on `py/v*` tags (e.g. `py/v1.3.0`)
- Previously both triggered on `v*` causing race conditions on the same GitHub Release

#### Go CI: bump to Go 1.25 (#18)
- `go-ci.yml` + `go-release.yml` updated from Go 1.24 → 1.25
- `golang.org/x/sync@v0.20.0` (transitive dep) requires Go ≥ 1.25 — CI was silently broken

### Housekeeping

#### Remove .bak backup files (#17)
- Migration script artefacts (`*.bak.*`) removed from git tracking
- `*.bak.*` pattern added to `.gitignore`

#### CONTRIBUTING.md (#26)
- Added comprehensive contributor guide covering:
  - Go + Python dev setup with exact commands
  - Project structure overview
  - Conventional commits format
  - Running tests (Go + Python with coverage)
  - PR requirements and CI gates
  - Release tag conventions (`go/v*` vs `py/v*`)
  - Code style guidelines (including LLMCaller injection pattern)

---

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
