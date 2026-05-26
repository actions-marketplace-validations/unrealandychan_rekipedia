# Changelog

## [0.17.19] - 2026-05-26
### Added
- `reki update --impact-only` — BFS-based selective wiki regeneration; only re-generates pages for transitively affected modules, reducing LLM calls by 80-90% on large repos. Closes #164.
- `reki ask --brief` / `REKIPEDIA_BRIEF=1` — compact answer mode (~150 tokens, 1 paragraph + file:line citations) closes #167
