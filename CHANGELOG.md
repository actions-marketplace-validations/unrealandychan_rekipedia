# Changelog

## [0.20.0] - 2026-06-01
### Added
- **Document extraction** (`rekipedia[docs]`): parse PDF, DOCX, PPTX, and XLSX files via `liteparse`. Opt-in via `documents.enabled: true` in `.rekipedia/config.yml`. Closes #199.
- `document_chunks` SQLite table (migration 006): stores page-level text and bounding boxes for all extracted document pages. Cascade-deleted when a scan run is removed. Closes #200.
- `reki embed` now includes document chunks in the FAISS index when `documents.embed_chunks: true` (default). Closes #201.
- `reki scan` auto-generates a wiki summary page per document file (e.g., `📄 api.pdf`) when `documents.wiki_page_per_doc: true` (default). Closes #203.
- `reki onboard` now shows a **📄 Documentation Files** table listing all PDF/DOCX/PPTX/XLSX files in the repo. Closes #204.
- New `documents` config section added to default config with sensible opt-in defaults. All existing repos unaffected until `enabled: true` is set.
### Changed
- `config/loader.py`: `load_config()` now merges built-in `_DEFAULT_CONFIG` before global and local overrides, ensuring all config keys always have a valid default.

## [0.19.0] - 2026-05-29
### Added
- `reki init --with-copilot`: writes `.vscode/mcp.json` (VS Code Copilot MCP, `"servers"` format) and enables `chat.mcp.enabled` in `.vscode/settings.json`.
- `reki init --with-codex`: writes `.codex/instructions.md` and `codex-mcp-hint.md` with Codex CLI `~/.codex/config.toml` setup instructions.
- `reki init --with-cursor`: writes `.cursor/mcp.json` and `.cursor/rules/rekipedia.mdc` with `alwaysApply: true`.
- `reki init --with-all-ai`: convenience flag — runs `--with-copilot`, `--with-codex`, and `--with-cursor` in one command.
- Two new MCP tools: `list_wiki_pages` (enumerate all wiki pages) and `get_wiki_page` (read a page by name). Available in `reki mcp` server.
- Per-tool tailored agent instruction files: `CLAUDE.md`, `AGENTS.md`, and `.github/copilot-instructions.md` now each contain tool-specific MCP setup instructions rather than a generic template.

## [0.18.0] - 2026-05-29
### Added
- `reki export --format bundle` — deterministic, content-addressed wiki snapshot with stable `bundle_id` and per-page hash trailers for team sync. Closes #182.
- `reki merge <bundle-A> <bundle-B> [--base BASE]` — three-way wiki merge with last-write-wins on unchanged pages and `<!-- reki:conflict -->` markers on genuine conflicts. Outputs `merge_report.json`. Closes #183.
- `reki merge-driver BASE OURS THEIRS` — git merge driver interface: exits 0 on clean merge, 1 on conflict. Write best-effort merged result to OURS. Closes #184.
- `reki init --with-merge-driver` — registers `.gitattributes` merge driver entry and `.git/config` merge driver config so `git merge` automatically uses rekipedia's wiki merge logic. Closes #184.
- `reki watch . --publish` — auto-publishes the wiki after every incremental update. Closes #185.
- `team.sync_dir` config key — default publish target for `reki watch --publish`. `team.auto_watch_publish: true` enables publish automatically without the flag. Closes #185.
- `reki pull [URL]` — fetch and merge a remote wiki bundle over HTTPS, S3 (`rekipedia[aws]`), or GCS (`rekipedia[gcs]`). Reads `team.remote_url` from config when URL is omitted. `--dry-run` previews without writing. Closes #186.
- `reki init --with-ci --with-upload s3|gcs` — appends an S3 or GCS bundle upload step to the generated GitHub Actions workflow. Closes #187.

## [0.17.22] - 2026-05-26
### Added
- `reki refactor --dry-run` — preview all suggested changes without writing files. Closes #166.
- `reki refactor --apply` — auto-apply safe smells (`dead_code`, `large_file`). Non-auto-fixable smells show guidance only.
- `reki refactor --apply --dry-run` — preview what `--apply` would do.


## [0.17.19] - 2026-05-26
### Added
- `reki update --impact-only` — BFS-based selective wiki regeneration; only re-generates pages for transitively affected modules, reducing LLM calls by 80-90% on large repos. Closes #164.
- `reki ask --brief` / `REKIPEDIA_BRIEF=1` — compact answer mode (~150 tokens, 1 paragraph + file:line citations) closes #167
