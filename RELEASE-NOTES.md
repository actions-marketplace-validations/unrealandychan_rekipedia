     1|## v0.17.0 — 2026-05-20

### New Features

**Benchmark evaluation suite** (closes #139)
- `benchmarks/` directory with extraction accuracy + performance benchmarks
- Fixture snapshots for Python/TypeScript codebases
- `benchmarks/run_extraction.py` script (--verbose, --json)
- CI job `.github/workflows/benchmark.yml` triggered on `py/v*` tags
- Baselines stored in `benchmarks/baselines.json`

**`reki affected`** — git-diff-aware minimal test selection (#136)

**Framework route extraction** — `kind="route"` symbols across Python/TS/Go/Rust (#137)

**`reki watch`** — native OS filesystem watcher + debounce (#138)

---

## v0.15.1 — unreleased
     2|
     3|### New Features
     4|
     5|**Streaming output for `reki ask`** (closes #125)
     6|- `reki ask` now renders answers using **rich Markdown live streaming** — headers, code blocks, bullet points, and inline code are rendered in real-time as the LLM produces tokens.
     7|- A spinner shows while waiting for the first token; once it arrives, the answer renders progressively inside a `rich.Live` panel.
     8|- Added `--no-stream` CLI flag to disable streaming and wait for the full response before printing. Useful for piping output or CI environments.
     9|- Added `REKIPEDIA_STREAM=0` environment variable as an alternative to `--no-stream`.
    10|- The REPL info panel now shows whether output mode is `streaming` or `buffered`.
    11|- Non-streaming mode uses `run_ask` (single LLM call with spinner), streaming mode uses `stream_ask` (litellm `stream=True`).
    12|
    13|---
    14|
    15|## v0.15.0 — 2026-05-13
    16|
    17|### Performance Improvements
    18|
    19|**SQLite Storage Layer** (closes #108, #109, #110, #111)
    20|- **Batch commits** — `upsert_files_batch()` and `upsert_pages_batch()` use `executemany` + single `commit()` instead of one commit per row; `upsert_page_sources()` likewise. For a 1,000-file repo, `reki scan` write phase is up to 50× faster.
    21|- **PRAGMA tuning** — `synchronous=NORMAL`, `cache_size=-64000` (64 MB), `temp_store=MEMORY` applied on connection open; 2–3× faster writes on local desktop.
    22|- **Schema introspection cache** — `_table_names()` now caches results in an instance variable instead of querying `sqlite_master` on every read/write call.
    23|- **SQL-side copy filtering** — `copy_unchanged_symbols()` and `copy_unchanged_relationships()` now use `INSERT … SELECT … WHERE file NOT IN (…)` entirely inside SQLite, eliminating full-table Python-side filtering.
    24|
    25|**Parallelism** (closes #112, #113)
    26|- **Parallel SHA-256 hashing** — `Snapshotter.snapshot()` now hashes files concurrently via `ThreadPoolExecutor(max_workers=8)`; unreadable files are skipped with a warning instead of aborting.
    27|- **Parallel shard extraction in `reki update`** — `run_update.py` now mirrors the `ThreadPoolExecutor` pattern from `run_digest.py`; per-shard errors are isolated and logged.
    28|
    29|**RAG / Embedder** (closes #114, #115, #116, #117, #118)
    30|- **Cached FAISS index + chunks** — `EmbedPipeline` caches `chunks.json` and the FAISS index as `cached_property`; subsequent `reki ask` calls in the same process skip disk I/O entirely.
    31|- **Single query embedding** — `search()` no longer embeds the query twice; the same vector is reused for both FAISS retrieval and MMR re-ranking, halving embedding API calls.
    32|- **O(1) MMR candidate lookup** — replaced nested linear scan with a `{(file, chunk_idx): idx}` dict; eliminates O(N²) behaviour on large indexes.
    33|- **Streaming FAISS index build** — `build()` adds each embedding batch to the index immediately and releases the vectors, keeping RAM usage proportional to one batch instead of the entire corpus.
    34|- **Rate-limit sleep gated behind env var** — the fixed `time.sleep(0.1)` between embedding batches is now off by default; set `REKIPEDIA_EMBED_RATE_LIMIT=1` to re-enable for hosted API rate limits.
    35|
    36|**PageBuilder** (closes #119)
    37|- **Module-level system prompt** — `_SYSTEM_PROMPT` is read from disk once at import time instead of on every `PageBuilder` construction.
    38|
    39|---
    40|
    41|## v0.14.0 — 2026-05-11
    42|
    43|### New Features
    44|- **Python API** — First-class programmatic interface: `rekipedia.scan()`, `rekipedia.ask()`, and async variants `scan_async()` / `ask_async()`. Returns typed `ScanResult` and `AskResult` dataclasses with citations. Import directly as `import rekipedia; rekipedia.scan("/path/to/repo")`. Closes #101.
    45|
    46|---
    47|
    48|## v0.13.0 — 2026-05-09
    49|
    50|### New Features
    51|- **Agentic Ask** — `reki ask` now supports a ReAct tool-calling loop (`REKIPEDIA_AGENT_ASK=1`). Instead of stuffing a 96K context window, the LLM iteratively calls `search_code`, `get_symbol`, `get_page`, `get_relationships`, and `finish` tools to retrieve exactly what it needs. Falls back to single-shot mode automatically if the model doesn't support tool calling. (#94)
    52|- **Agentic Planner** — `reki scan` wiki planner supports tool-calling mode (`REKIPEDIA_AGENT_PLANNER=1`). The LLM builds the wiki plan incrementally using `add_section`, `add_page`, and `finalize` tools instead of generating a single large JSON blob. (#94)
    53|
    54|## v0.12.0 — 2026-05-08
    55|
    56|### Bug Fixes
    57|- **Go shard ID overflow** — shard IDs no longer corrupt at idx≥10; switched from rune arithmetic to `fmt.Sprintf` (#86)
    58|- **Token budget unified** — Python default raised 12K→40K to match Go; both now respect `REKIPEDIA_SHARD_TOKEN_BUDGET` env var (#87)
    59|- **LLMClient.stream() dead code** — removed redundant api_key/base_url assignments already covered by `_base_kwargs()` (#89)
    60|- **wiki_pages mtime cache** — `_wiki_pages()` now caches with directory mtime check instead of reading disk on every request (#90)
    61|- **Frontmatter dedup** — `_summary_html()` now uses `_strip_yaml_frontmatter()` instead of inline duplicate logic (#91)
    62|- **Go chunker cleanup** — removed unused `lines` param from `countLines`; eliminates wasted `strings.Split` allocation (#92)
    63|- **Go embedder min() shadow** — removed local `min()` that shadowed Go 1.21+ builtin (#93)
    64|- **Context priority unified** — Python and Go `run_ask` now assemble context in same order: RAG → notes → wiki → symbols (#97)
    65|
    66|### Refactoring
    67|- **run_ask/stream_ask** — shared preamble extracted into `_prepare_ask()` helper; eliminates code duplication (#88)
    68|
    69|## v0.11.1 — 2026-05-08
    70|
    71|### Bug Fixes
    72|- **`/notes` page crash** — `notes_page` was using the old Starlette `TemplateResponse` API (`TemplateResponse("template", dict)`) while all other endpoints had already migrated to the new signature (`TemplateResponse(request, "template", ctx)`). Caused `TypeError: cannot use 'tuple' as a dict key` on Python 3.14 + new Starlette. Fixed to use `_ctx()` helper consistently.
    73|
    74|## v0.11.0 — 2025-01-XX
    75|
    76|### New Features
    77|- **Codebase ToC Tree** (#85): scan now builds a `codebase_tree` table in SQLite with full directory/file hierarchy. Each node records path, name, kind (file/dir), language, parent reference, and depth. Lays groundwork for reasoning-based hierarchical retrieval (Phase 2).
    78|
    79|### Go
    80|- Added `models.TreeNode` struct
    81|- Added `storage.UpsertTree()` and `storage.GetTree()` methods
    82|- `RunDigest` now populates `codebase_tree` after snapshot
    83|
    84|## v0.10.9 — 2026-xx-xx
    85|
    86|### New Features
    87|- **Symbol-boundary chunking** (`#78`): RAG chunks for Python, TypeScript, and Go files now align to AST symbol boundaries (functions, classes, methods) using tree-sitter. Chunks no longer cut through function definitions mid-statement, resulting in more semantically coherent RAG context. Falls back to character-based chunking when tree-sitter is unavailable or the language is unsupported.
    88|
    89|## v0.10.8 — 2026-xx-xx
    90|
    91|### New Features
    92|- **Targeted wiki re-synthesis** (`#77`): `reki update` now tracks which source files contributed to each wiki page (`page_sources` table, migration 005). On update, only pages whose sources changed are re-synthesised. Unaffected pages are carried forward at zero LLM cost. Falls back to full re-synthesis if page sources not yet recorded (first update after upgrade).
    93|
    94|## v0.10.7 — 2026-xx-xx
    95|
    96|### New Features
    97|- **Incremental embed on `reki update`** (`#76`): `reki update` now automatically refreshes the RAG index — only re-embedding chunks from changed files. Unchanged files carry forward their embeddings at zero API cost. New `EmbedPipeline.update()` method and `SqliteStore.carry_forward_rag_chunks()`. Expect ~90% fewer embedding API calls on typical updates.
    98|
    99|## v0.10.6 — 2026-05-07
   100|
   101|### New Features
   102|- **Chunk-level provenance** (`#75`): RAG chunks now track `file_path`, `start_line`, `end_line`, `start_char`, `end_char`, and `text_hash` in `store.db`. New `rag_chunks` table (migration 004) and `SqliteStore` methods: `upsert_rag_chunks()`, `get_rag_chunks_by_file()`, `get_all_rag_chunks()`. Foundation for incremental re-embedding in #76.
   103|- `EmbedPipeline` accepts optional `store` and `run_id` params — when provided, provenance is automatically persisted after each `reki embed` run.
   104|- `_chunk_file()` now includes `start_line`, `end_line`, `end_char`, `text_hash` in every chunk dict.
   105|
   106|## v0.10.5 — Tech Lead Notes
   107|
   108|### New Features
   109|- **Note storage** (#62): persistent `tech_lead_notes` table in SQLite, independent of scan runs
   110|- **Note CLI** (#63): `reki note add/list/remove/edit/import` commands (Python + Go)
   111|- **RAG injection** (#64): relevant notes auto-injected into `reki ask` context as high-priority team context
   112|- **Batch import** (#65): `reki note import notes.yml` / `reki note import TECH_CONTEXT.md`
   113|- **Web UI** (#66): `/notes` management page in `reki serve` with tag filtering and inline add/delete
   114|
   115|# Release Notes
   116|
   117|## v0.10.4 — Fix Docker Sandbox Missing tree-sitter Dependencies
   118|
   119|### Bug Fix
   120|- **Docker sandbox `ModuleNotFoundError`**: `Dockerfile.sandbox` was missing `tree-sitter`, `tree-sitter-go`, `tree-sitter-python`, `tree-sitter-typescript`, `tree-sitter-rust`, `tree-sitter-java` — Go shards (and others) would always fail inside the Docker sandbox.
   121|
   122|---
   123|
   124|## v0.10.3 — Wiki Generation Quality Improvements
   125|
   126|### Improvements
   127|- **Symbol sample sorted by importance**: Planner summary now shows `impl` files first, CI/test/config files last — LLM sees relevant source code, not GitHub Actions scripts.
   128|- **File role classification**: Each symbol and relationship tagged with `file_role` (`impl`/`test`/`ci`/`config`/`doc`) in planner payload — LLM can filter noise.
   129|- **Planner summary enhanced**: Includes `file_role_counts`, per-dir language breakdown, and multi-language instructions so LLM creates per-language pages for polyglot repos.
   130|- **Architecture diagram improved**: Module graph now groups by top-level module (not individual symbols), filters external/stdlib packages, limits to top-20 modules by edge count — produces readable Mermaid diagrams.
   131|- **Importance scores fixed**: Wiki pages now correctly inherit importance from planner spec (was always defaulting to 50).
   132|
   133|---
   134|
   135|## v0.9.38 — Refactor Analysis Pipeline
   136|
   137|### New Features
   138|- **`reki refactor` command** (Python + Go): Standalone command to detect code smells and generate `REFACTOR.md` + `refactor_report.json` without running a full scan.
   139|- **Static analysis detectors** (Python + Go): Five detectors — `god_class`, `circular_dep`, `dead_code`, `large_file`, `high_coupling` — plus graph metrics: `high_fan_in`, `high_fan_out`, `deep_inheritance`.
   140|- **LLM enrichment** (`--no-llm` to skip): Each detected issue gets an AI-generated problem statement, concrete refactoring suggestion, safest starting point, and risk level.
   141|- **REFACTOR.md output**: Human/agent-readable Markdown guide grouped by severity (🔴 High / 🟡 Medium / 🟢 Quick Wins).
   142|- **`refactor_report.json` output**: Machine-readable JSON report for CI/tooling integration.
   143|- **`--with-refactor` flag on `reki scan`**: Auto-generate REFACTOR.md after scan completes.
   144|- **`--stdout` flag**: Print REFACTOR.md to stdout for piping (`reki scan . --stdout | claude`).
   145|- **`--no-llm` flag**: Run static analysis only, skip LLM enrichment.
   146|
   147|### Internal
   148|- New `refactor_types.go` — unified `RefactorIssue` struct (single source of truth across detector, enricher, writer).
   149|- `Metrics` field unified to `map[string]any` across all Go refactor files.
   150|- Python + Go feature parity: identical detectors, thresholds, severity levels, and output format.
   151|
   152|---
   153|
   154|## v0.9.37 — Go UI sync: sidebar search + section grouping
   155|
   156|### Changes
   157|- **Go `base.html` rewrite**: Full feature-parity with Python UI — sidebar now shows wiki pages grouped by `section` frontmatter field with collapsible category headers.
   158|- **Search bar**: Live full-text search input at top of sidebar (250ms debounce), calls `/api/wiki/search`, shows title + snippet + section label. Escape to return to category view.
   159|- **Design refresh**: Migrated to GitHub-style CSS variables (`--bg`, `--surface`, `--accent`, etc.) matching Python side exactly.
   160|
   161|---
   162|
   163|## v0.9.36 — Go sync: file-level graph + wiki full-text search
   164|
   165|### Changes
   166|- **Go `handleAPIGraph` rewrite**: Migrated to file-level dependency graph (nodes = source files, edges = import relationships). Matches Python v0.9.35 behaviour — `moduleCandidates()` resolves dotted module paths to `.py`/`.go`/`.ts`/`.js` file candidates.
   167|- **Go `/api/wiki/search` (new)**: Full-text search across wiki page title, section, and body content. Returns slug, title, section, snippet, and title_match flag — feature-parity with Python v0.9.34.
   168|- **`graphNode` struct**: Added `file` and `group` JSON fields for file-level graph display.
   169|
   170|---
   171|
   172|## v0.9.35 — Wiki Categories & Search
   173|
   174|### New Features
   175|- **Sidebar category grouping**: Wiki pages are now grouped by their `section` frontmatter field in the sidebar. Each group has a collapsible header — click to expand/collapse.
   176|- **Live search filter**: Search box at the top of the wiki nav filters pages by title or section as you type. Matching groups auto-expand; empty groups are hidden.
   177|- **Frontmatter `section` read by server**: `_wiki_pages()` now parses frontmatter YAML to extract both `title` and `section` fields, passing them to templates.
   178|
   179|---
   180|
   181|## v0.9.31 — Scan skip + Ask positional arg
   182|
   183|### New Features
   184|- **Scan skip-if-scanned** (Python + Go): `reki scan` skips if a `status='success'` run already exists in the DB. Use `--force`/`-f` to rescan.
   185|- **`reki ask` positional arg**: `reki ask "your question"` now works directly without `-q` flag (Python + Go aligned).
   186|
   187|---
   188|
   189|## v0.9.30 — Frontmatter integrity fix
   190|
   191|### Bug Fixes
   192|- **`_ensure_frontmatter` always strips+rebuilds**: Prevents LLM hallucination garbage fields (e.g. `created_at: 0.9.23`) from surviving in wiki frontmatter.
   193|- **`_strip_yaml_frontmatter` handles malformed FM**: Strips frontmatter even if closing `---` is missing; fallback to first blank line or `#` heading.
   194|
   195|---
   196|
   197|## v0.9.29 — Agent & MCP integration
   198|
   199|### New Features
   200|- **MCP `ask` tool** (#59): `reki mcp` now exposes an `ask` tool — agents can ask natural-language questions about the codebase grounded in wiki + RAG. Works with Claude Code, Cursor, and any MCP client.
   201|- **Auto agent hint files** (#60): `reki scan` now auto-generates `CLAUDE.md`, `AGENTS.md`, and `.github/copilot-instructions.md` with instructions for AI agents to use `reki ask` and the MCP server.
   202|- **Auto `.mcp.json`** (#61): `reki scan` auto-generates `.mcp.json` in the repo root for Claude Code MCP auto-discovery. Merges with existing entries; adds `.mcp.json` to `.gitignore`.
   203|
   204|## v0.9.28 — Embed base URL isolation fix
   205|
   206|### Bug Fixes
   207|- **`embed_base_url` no longer falls back to `base_url`**: `reki embed` and `reki scan` previously used the LLM chat endpoint as the embedding base URL when `embed_base_url` was unset. This caused proxy misrouting. Both `embed.py` and `scan.py` now default to `""` (use provider default) unless `embed_base_url` / `REKIPEDIA_EMBED_BASE_URL` is explicitly set.
   208|
   209|---
   210|
   211|## v0.9.27 — Embedding refactor + test fixes
   212|
   213|### Changes
   214|- **Embedding via litellm unified path**: `_embed_batch` now always uses `litellm.embedding()` — `base_url` is passed as `api_base` parameter instead of raw httpx calls. Simpler, more reliable, supports all litellm providers consistently.
   215|- **Tests updated**: `test_embed_batch_with_base_url` and `test_embed_batch_with_base_url_error` updated to mock litellm instead of httpx.
   216|
   217|---
   218|
   219|## v0.9.26 — Ask & Search Quality Improvements
   220|
   221|### New Features
   222|- **BM25 Symbol Search** (#52): `reki search` now uses BM25 scoring with camelCase/snake_case tokenization. Queries like `"entry point"` now find `main_entrypoint`. New `--kind` filter option. Go side updated with same tokenization logic.
   223|- **Planner Keywords Field** (#54): Each generated wiki page now includes a `keywords: [...]` frontmatter field listing 5–10 exact symbol names and domain terms the page covers. Used by the ask pipeline for fast page routing.
   224|- **Ask Page Relevance Ranking** (#53): `reki ask` now ranks wiki pages by query relevance (TF scoring + `keywords` frontmatter + `importance` boost) before context assembly. Prevents relevant pages from being pushed out of the token budget by alphabetically-prior irrelevant pages.
   225|- **RAG MMR Deduplication** (#55): After FAISS top-K retrieval, Maximal Marginal Relevance (MMR) diversifies results. Near-duplicate chunks from the same function are de-prioritised, ensuring broader coverage. Opt-out via `REKIPEDIA_RAG_MMR=0`.
   226|- **Silent Query Rewriting** (#56): `reki ask` silently rewrites natural-language questions to match codebase vocabulary before retrieval (e.g. `"how does login work"` → `"how does AuthService.authenticate / verify_credentials work"`). Opt-out via `--no-rewrite` or `REKIPEDIA_QUERY_REWRITE=0`.
   227|
   228|---
   229|
   230|## v0.9.25 — Graph Intelligence & Developer Tools
   231|
   232|### New Features
   233|- **Knowledge Gap Detection** (#43): Identifies untested hotspots — high call-count symbols with no test coverage. `knowledge_gaps` injected into wiki payload.
   234|- **Graph Diff / Snapshot Comparison** (#44): `reki diff` compares two timestamped scan snapshots. Auto-saves snapshots in `.rekipedia/snapshots/`.
   235|- **Hub & Bridge Node Detection** (#45): Degree-based centrality analysis. `hub_nodes` injected into wiki payload. Bridge nodes (high in+out degree) flagged.
   236|- **Blast-Radius / Impact Analysis** (#46): `reki impact <file>` — BFS traversal shows all affected files, symbols, and tests for a changed file.
   237|- **D3.js Interactive Graph** (#47): `/graph` route in `reki serve` — force-directed graph with edge filter, node search, section colour-coding.
   238|- **MCP Server** (#48): `reki mcp` starts a JSON-RPC 2.0 MCP stdio server with 6 tools: get_context, search_nodes, get_relationships, get_knowledge_gaps, get_hub_nodes, get_impact.
   239|- **Multi-Repo Watch Daemon** (#49): `reki watch add/start/list/remove` — background file watcher with debounced auto-indexing via `watchdog`.
   240|- **Cross-Repo Search** (#50): `reki search <query> [--all-repos]` — parallel fan-out search across all registered repo DBs.
   241|- **Graph Export** (#51): `reki export --format graphml|cypher|obsidian` — export to GraphML, Neo4j Cypher, and Obsidian wikilink vaults.
   242|
   243|### Fixes
   244|- Snapshot timestamp now uses microseconds to avoid collision when saving multiple snapshots in the same second.
   245|- `tree-sitter-go`, `tree-sitter-java`, `tree-sitter-python`, `tree-sitter-typescript` installed in dev venv for full test suite.
   246|
   247|---
   248|
   249|## v0.9.24 — Fix Python CI: Add `_build_cross_module_summary` + slug/frontmatter hardening
   250|
   251|### Fix: Python CI ImportError (`_build_cross_module_summary` missing)
   252|- `tests/test_page_builder_relationships.py` imported `_build_cross_module_summary` from `page_builder` but the function did not exist in source
   253|- Added `_build_cross_module_summary(relationships, symbols, files_seen)` — builds a per-module relationship map with `imports/imported_by`, `calls/called_by`, `inherits/inherited_by` keys; deduplicates edges; caps at 100 modules
   254|- `_build_payload` now includes three new fields: `relationship_stats` (total + by_kind counts), `internal_relationships` (stdlib-filtered, capped at 800), `cross_module_summary`
   255|- Increased `relationships` payload limit from 600 → 1500
   256|
   257|### Fix: Slug sanitization + frontmatter hallucination stripping (Python & Go)
   258|- `_sanitize_slug()` / `sanitizeSlug()` added to both sides — normalises LLM-generated slugs to `lowercase-hyphenated`, collapses runs, strips bad chars
   259|- `_ensure_frontmatter()` (Python) now always strips and rebuilds frontmatter — eliminates hallucinated keys like `created_at`, `author`, `date`
   260|- `ensureFrontmatter()` (Go) added — was completely missing; Go now matches Python behaviour
   261|- Planner slug sanitization applied immediately after JSON parse on both sides
   262|
   263|## v0.9.23 — Fix Go Release CI & Remove close-wiki Branding
   264|
   265|### Fix: Go Release CI Homebrew tap 404
   266|- `update-homebrew-tap.py` BASE_URL was pointing to `rekipedia-releases` repo → corrected to `rekipedia` main repo
   267|- `.goreleaser.yaml` release target + brew url_template also updated to `rekipedia` repo
   268|
   269|### Fix: Remove all `close-wiki` branding
   270|- `base.html` sidebar title/subtitle: `close-wiki` → `rekipedia`
   271|- `index.html` quick-start example: `close-wiki scan .` → `rekipedia scan .`
   272|- All 4 occurrences removed (verified via grep)
   273|
   274|---
   275|
   276|## v0.9.22 — Mermaid Diagrams Now Render in Wiki Pages
   277|
   278|### Mermaid.js rendering in wiki pages (Python + Go)
   279|- All ` ```mermaid ` code blocks in wiki pages now **render as actual diagrams** instead of raw code
   280|- Dark theme matching rekipedia's colour scheme (navy background, blue accent, gold highlights)
   281|- HTML entity unescape fix: `markdown` library encodes `-->` as `--&gt;` — fixed before passing to Mermaid.js
   282|- **"🕸 Open in Graph"** button appears on every `flowchart` / `classDiagram` — links to interactive D3 force graph
   283|- **`{ }` toggle button** shows/hides raw Mermaid source for any diagram
   284|- Render errors show inline with raw source fallback (no silent failures)
   285|
   286|---
   287|
   288|## v0.9.21 — Fix D3 Graph Edges Not Showing
   289|
   290|### Fix: Graph API multi-strategy ID resolution (#graph-edges)
   291|- **Root cause**: relationship `from_`/`to` names (e.g. `rekipedia.cli.scan`, `PageBuilder.build`) didn't match node IDs (format: `file::name`) → JS filter silently dropped all unresolved edges → only 6 edges visible for 1898 nodes
   292|- **Fix**: replaced O(n) linear scan with O(1) dict lookup + 4-strategy resolver:
   293|  1. Exact label match
   294|  2. Already a valid node ID
   295|  3. Dotted module name → last segment (`rekipedia.cli.scan` → `scan`)
   296|  4. `Class.method` format → method name
   297|- Self-loops dropped; edges capped at **2000** prioritised by kind (`inherits > calls > imports`)
   298|- Response now includes `edge_count_total` field
   299|- Go server applies same logic
   300|- Added debug warning in graph.html for any remaining unresolved edges
   301|
   302|---
   303|
   304|## v0.9.20 — Richer Wiki Generation with Cross-Module Relationship Analysis
   305|
   306|### Pre-computed cross-module summary in payload
   307|- `_build_payload()` now pre-computes a `cross_module_summary` map grouping all internal `imports`, `calls`, and `inherits` relationships by module — top 100 most connected modules
   308|- Added `relationship_stats` field `{total, by_kind}` so LLM knows relationship coverage
   309|- Added `internal_relationships` field (stdlib-filtered, up to 800 internal edges)
   310|- Relationship limit increased from 600 → **1500** (Python + Go)
   311|
   312|### Stronger prompts for architecture and core-modules pages
   313|- `architecture` page focus now requires: Cross-Module Dependency Map (Mermaid `flowchart LR` + table), Module Coupling Analysis (tightly coupled pairs, isolated modules, circular imports)
   314|- `core-modules` page focus now requires per-module: Imports From, Imported By, Calls, Called By, Coupling Score — plus a summary cross-module table covering all documented modules
   315|
   316|### digest_system.md — mandatory cross-module rules
   317|- New "Cross-Module Relationship Rules" section: dependency table format, per-slug coverage rules, call chain tracing, coupling analysis
   318|- LLM now required to use `cross_module_summary` data directly instead of inferring from raw edges
   319|
   320|### Go page builder upgraded to match Python quality
   321|- `pageSystemPrompt` rewritten with full Mermaid rules, source citation rules, cross-module rules
   322|- Added `pageExtraFocus` entries for `architecture`, `core-modules`, `algorithms`, `cli-and-api` slugs
   323|- Go `buildPayload()` relationship limit 200 → 1500, added `cross_module_summary` and `relationship_stats`
   324|
   325|---
   326|
   327|## v0.9.19 — Diagram & Relationship Bug Fixes
   328|
   329|### Fix: diagram builder showing empty for all projects (#41)
   330|- **Bug 1 — Storage layer**: `get_all_relationships()` returned raw SQLite tuples; `dict(row)` on a flat tuple raises `TypeError` which was silently caught, making every relationship an empty dict. Fixed with explicit column selection and named dict construction
   331|- **Bug 2 — Go struct embedding**: Struct embedding (Go's form of composition/inheritance) was never extracted. Fixed by detecting `field_declaration` nodes without `field_identifier` and emitting `kind="inherits"` relationships for direct (`Animal`), pointer (`*Dog`), and cross-package (`pkg.Bar`) embedding
   332|- **Go stdlib filter**: Added common Go stdlib packages (`fmt`, `strings`, `sync`, `net`, `context`, etc.) to external prefix filter in `diagram_builder.py` — previously shown as internal module relationships
   333|
   334|---
   335|
   336|## v0.9.18 — Knowledge Diff, D3 Graph Filter & Homebrew License Fix
   337|
   338|### `reki diff` command — commit-level knowledge diff (#38)
   339|- `rekipedia diff --from-ref HEAD~1 --to-ref HEAD` shows added/removed/changed symbols between commits
   340|- Reads previous snapshot via `git show <ref>:.rekipedia/exports/symbols.json`
   341|- Outputs diff in markdown or plain text format (`--format md|text`)
   342|- Gracefully handles empty/missing stores (shows all current symbols as added)
   343|- Both Python and Go implemented
   344|
   345|### D3 graph search, filter & N-hop focus (#39)
   346|- **Search/filter**: type in search box to filter nodes by name or file — non-matching nodes fade to 20% opacity
   347|- **Group by file**: toggle button clusters and color-codes nodes by source file
   348|- **N-hop focus**: click a node to highlight 1-hop neighbours; click again to expand to 2-hop; click background to reset
   349|- All features preserve existing dark theme and gold god-node styling
   350|- Both Python (FastAPI) and Go server templates updated
   351|
   352|### Homebrew Formula license fix (#40)
   353|- Fixed `license "Proprietary"` → `license :cannot_represent` (correct Ruby symbol for SPDX-incompatible licenses)
   354|- Updated both `update-homebrew-tap.py` script and live `homebrew-tap/Formula/rekipedia.rb`
   355|
   356|---
   357|
   358|## v0.9.17 — Agent Context, Wiki Frontmatter & Scan Progress
   359|
   360|### `reki context` command — agent-ready output (#35)
   361|- `rekipedia context [REPO] --output context.md` generates a condensed single-file wiki for injection into coding agents
   362|- `--max-tokens N` flag (default 32,000) truncates output to fit agent context windows
   363|- Output includes YAML frontmatter + all wiki sections + top symbols
   364|- Both Python and Go implemented
   365|
   366|### YAML frontmatter for wiki pages (#36)
   367|- Every generated `.rekipedia/wiki/*.md` page now includes YAML frontmatter:
   368|  ```yaml
   369|  ---
   370|  title: Architecture Overview
   371|  created_at: 2026-05-03T10:00:00Z
   372|  rekipedia_version: 0.9.16
   373|  importance: 95
   374|  section: architecture
   375|  tags: []
   376|  pin: false
   377|  ---
   378|  ```
   379|- Compatible with Obsidian, Jekyll, and CI automation
   380|- Go `page_builder.go` updated with `ensureFrontmatter()` helper
   381|- Existing frontmatter not duplicated on re-scan
   382|
   383|### Scan progress display with ETA (#37)
   384|- `reki scan` now shows Rich progress bars for both phases:
   385|  - `🔍 Shard X/N` — extraction phase with ETA
   386|  - `📝 Page X/N` — wiki synthesis phase with ETA
   387|- Uses `rich.progress` with `SpinnerColumn`, `BarColumn`, `TimeRemainingColumn`
   388|- Go orchestrator updated with pterm progress bar for page synthesis
   389|- Existing `progress` callback still fires alongside visual display
   390|
   391|### Tests
   392|- **306 Python tests pass** | **Go: all 14 packages pass**
   393|- 17 new tests: context cmd (7), wiki frontmatter (6), scan progress (4)
   394|
   395|---
   396|
   397|
   398|
   399|### Multi-language AST Extractors (#32)
   400|- Added Go extractor using `tree-sitter-go` — extracts functions, structs, interfaces, imports; detects `func main()` entry point
   401|- Added Rust extractor using `tree-sitter-rust` — extracts `fn`, `struct`, `trait`, `use`; `impl Foo for Bar` produces `uses` relationship
   402|- Added Java extractor using `tree-sitter-java` — extracts classes, methods, imports; `extends` → `inherits`, `implements` → `uses`
   403|- All three extractors registered in `ALL_EXTRACTORS` by file extension (`.go`, `.rs`, `.java`)
   404|- 21 new tests (7 per extractor): symbol extraction, relationship detection, entry point, empty file handling
   405|
   406|### Multi-turn Conversation Memory for `reki ask` (#33)
   407|- `reki ask` REPL now maintains full conversation history across turns — follow-up questions have context
   408|- History passed as `messages[]` to LLM (litellm multi-turn format)
   409|- `--history-limit N` flag (default: 10 turns) — oldest turns dropped when limit exceeded
   410|- `--no-save-session` flag to skip disk persistence
   411|- Session auto-saved to `.rekipedia/sessions/<timestamp>.json` on exit
   412|- Turn number shown in prompt: `[1] ❯`, `[2] ❯`, …
   413|- 7 new tests covering history accumulation, limit truncation, session JSON persistence
   414|
   415|### Go Binary Feature Parity (#34)
   416|- `reki embed` — vector embedding pipeline in Go (chromem-go, no CGO)
   417|- `reki export` — wiki bundle to markdown or JSON from SQLite store
   418|- `reki update` — incremental re-scan (diff manifest vs current files, only re-process changed files)
   419|- 10 new Go tests covering all three commands
   420|
   421|### Test Fixes & CI Improvements
   422|- Fixed `python-multipart` missing dependency (FastAPI Form support)
   423|- Fixed `--cov=src/rekipedia` → `--cov=rekipedia` for installed wheel coverage tracking
   424|- Fixed homebrew tap version strip (`${TAG#go/v}`) — was incorrectly building `vgo/v0.9.15` URLs
   425|- Added `--skip=validate` to goreleaser for prefixed tag workflow
   426|- Updated Homebrew Formula license: `"MIT"` → `"Proprietary"`
   427|- Updated `README.md` license section: MIT → Proprietary & Confidential
   428|- **289 Python tests pass** | **Go: all 14 packages pass**
   429|
   430|---
   431|
   432|## v0.9.14 — Phase 5 & 6: Graph UI + Extraction Quality
   433|
   434|### Phase 5: Interactive Dependency Graph
   435|
   436|#### `/graph` route with D3.js force-directed visualization (#27)
   437|- `rekipedia serve` now exposes a `/graph` route rendering the full symbol dependency graph
   438|- D3.js force-directed layout with dark theme and zoom/pan support
   439|- God nodes (highest-degree symbols) highlighted with a distinct colour and larger radius
   440|
   441|### Phase 6: Extraction Quality
   442|
   443|#### Relationship confidence scoring (#28)
   444|- Every extracted `Relationship` now carries a `confidence: float` (0.0–1.0) and an `evidence_tag: Literal["EXTRACTED", "INFERRED", "AMBIGUOUS"]`
   445|- Default values are `1.0` / `"EXTRACTED"` so existing code is fully backward-compatible
   446|- LLM-inferred edges receive `INFERRED`; ambiguous cross-shard edges receive `AMBIGUOUS`
   447|
   448|#### Design rationale extraction (#29)
   449|- Python extractor now collects `# NOTE:`, `# HACK:`, `# WHY:` (and `# IMPORTANT:`, `# TODO:`) inline comments
   450|- Each comment is stored as a `RationaleNote` inside `AnalysisResult.rationale_notes`
   451|- Rationale notes appear as lightweight knowledge nodes on the `/graph` route and in wiki pages
   452|
   453|#### God nodes ranking (#30)
   454|- `rekipedia.analysis.graph_analysis.compute_god_nodes()` computes in+out degree for every symbol
   455|- Top-10 god nodes are surfaced in `index.md` under a **Key Symbols** section
   456|- `/graph` highlights them for at-a-glance architectural understanding
   457|
   458|#### Git hooks auto-rebuild (#31)
   459|- `rekipedia hook install` writes a `post-commit` hook that runs `rekipedia update` in the background after every commit
   460|- `rekipedia hook uninstall` removes only hooks managed by rekipedia (safe for pre-existing hooks)
   461|- `rekipedia hook status` shows install state and last-modified timestamp
   462|
   463|---
   464|
   465|## v0.9.13 — Security Hardening, Testability & DX Improvements
   466|
   467|
   468|### Security
   469|
   470|#### Path traversal protection (#19)
   471|- Go server: wiki slug validated against `^[a-zA-Z0-9_-]+$` before building filepath — rejects dots, slashes, and special characters with 404
   472|- Python FastAPI server: same regex guard added to `/wiki/{slug}` handler
   473|
   474|#### Go HTTP server timeouts (#20)
   475|- `http.Server` now sets `ReadTimeout=15s`, `WriteTimeout=60s`, `IdleTimeout=120s`
   476|- Prevents slow-loris DoS and resource exhaustion from idle connections
   477|
   478|### Reliability
   479|
   480|#### Real `/api/health` DB probe (#23)
   481|- `/api/health` now opens and probes `store.db` instead of returning a static `{"status":"ok"}`
   482|- Returns `{"status":"degraded","db":"error:..."}` + HTTP 503 when DB is unavailable
   483|- Returns `{"status":"ok","db":"no_store"}` when no scan has been run yet
   484|- Both Go and Python servers updated
   485|
   486|### Testability
   487|
   488|#### LLMCaller interface injection (#22)
   489|- **Go**: `llm.Caller` interface (`Call` + `StreamCall`) extracted from `*llm.Client`
   490|  - `llm.FakeCaller` test double with configurable `Response`/`StreamChunks`/`CallErr`
   491|  - `AskOptions.Caller` + `DigestOptions.Caller` fields for injection
   492|  - `synthesis.NewPlannerAgent` + `NewPageBuilder` now accept `llm.Caller` (was `*llm.Client`)
   493|- **Python**: `LLMCaller` runtime-checkable `Protocol` with `call`/`stream` methods
   494|  - `FakeCaller` test double
   495|  - `PlannerAgent` + `PageBuilder` accept `caller=` keyword argument
   496|
   497|### CI / CD
   498|
   499|#### Python CI: pytest + coverage gate (#21, #25)
   500|- Python CI now runs full `tests/` suite (was smoke test only)
   501|