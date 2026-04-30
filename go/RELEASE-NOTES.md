# Release Notes

## v0.9.0

### New Features
- **Go AST extractor** — Native Go source code analysis using `go/ast` stdlib (zero external dependencies)
- **`--languages` flag** — Filter scan/update by language (e.g. `--languages go,python,typescript`)
- **Flag parity** — All commands (`ask`, `serve`, `update`, `embed`) now have full flag parity with Python CLI
- **`--host` flag for `serve`** — Configure host:port instead of hardcoded `:7070`

### Improvements
- GoReleaser config with multi-platform builds (darwin/linux/windows × amd64/arm64)
- Homebrew tap auto-update on release

### Bug Fixes
- Fixed hardcoded host in `serve` command
- Added missing `--output-dir` and `--no-docker` flags across commands
