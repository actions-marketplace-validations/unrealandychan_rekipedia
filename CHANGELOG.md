# Changelog

## [0.17.22] - 2026-05-26
### Added
- `reki refactor --dry-run` — preview all suggested changes without writing files. Closes #166.
- `reki refactor --apply` — auto-apply safe smells (`dead_code`, `large_file`). Non-auto-fixable smells show guidance only.
- `reki refactor --apply --dry-run` — preview what `--apply` would do.


## [0.17.19] - 2026-05-26
### Added
- `reki update --impact-only` — BFS-based selective wiki regeneration; only re-generates pages for transitively affected modules, reducing LLM calls by 80-90% on large repos. Closes #164.
- `reki ask --brief` / `REKIPEDIA_BRIEF=1` — compact answer mode (~150 tokens, 1 paragraph + file:line citations) closes #167
