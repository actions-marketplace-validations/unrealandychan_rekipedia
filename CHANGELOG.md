# Changelog

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
