---
slug: contributing
title: "Contributing"
section: development
tags: [contributing, testing]
pin: false
importance: 50
created_at: 2026-05-05T04:25:56Z
rekipedia_version: 0.10.2
---

# Contributing

This repository has a fairly opinionated contributor workflow built around the existing tooling in `Makefile`, `pyproject.toml`, `package.json`, and the Go module under `go/`. The most reliable way to make a change is to run the same build and test commands used by the project’s CI and local automation, then validate the relevant repo-specific checks before opening a PR.

## Local Development

The repo is split across Python and Go tooling, with a small Node entrypoint as well. For contributor work, the main development surfaces are:

- Python source under `src/rekipedia/`
- Go implementation under `go/`
- JS wrapper script in `bin/rekipedia.js`
- tests under `tests/` and `go/**/_test.go`

The repository includes environment and setup hints in files like `.env.sample`, `AGENTS.md`, `CLAUDE.md`, and `README.md`, but the operational workflow is driven by the build/test commands that are already checked in.

### Recommended setup loop

A practical local loop is:

```bash
# Python project
uv build
pytest

# Go project
cd go
go test ./... -v -count=1 -timeout 120s
CGO_ENABLED=0 go build -ldflags "-s -w" -o /tmp/reki ./cmd/rekipedia

# Optional Node build
npm run build  # tsc
```

There are also packaging-oriented commands in the repo’s build metadata:

- `hatch build`
- `docker build .`

For Go-specific contributor work, the `go/README.md` and `go/Makefile` suggest the Go subtree can be treated as a self-contained build target. The entrypoint is [`main`](go/cmd/rekipedia/main.go#L6) in the Go CLI, which dispatches into the command tree defined under `go/cmd/rekipedia/cmd/`.

> **Sources:** `Makefile` · `package.json` · `pyproject.toml` · `go/README.md` · `go/cmd/rekipedia/main.go` · L6–L8 · [`main`](go/cmd/rekipedia/main.go#L6)

## Running Tests

The repository’s test coverage is intentionally broad and split by implementation area. The top-level test command is Python-centric:

```bash
pytest
```

For the Go codebase, the canonical command is:

```bash
go test ./... -v -count=1 -timeout 120s
```

That command is important because it forces fresh execution (`-count=1`) and gives the test suite a 120-second ceiling, which aligns with the repo’s own build/test expectations. The Go tests are organized around functionality such as CLI commands, analysis, orchestration, storage, server behavior, and synthesis. Examples include [`TestRootCommandHasSubcommands`](go/cmd/rekipedia/cmd/root_test.go#L19), [`TestHookInstall`](go/cmd/rekipedia/cmd/hook_test.go#L20), [`TestDetectGodNodes_DetectsHub`](go/internal/analysis/refactor_detector_test.go#L23), and [`TestAPIGraph`](go/internal/server/server_test.go#L203).

For Python-specific validation, the repository includes tests under `tests/` such as:

- `tests/test_server.py`
- `tests/test_page_builder.py`
- `tests/test_sqlite_store.py`
- `tests/test_watcher.py`

and a narrower invocation is also present in the recorded commands:

```bash
pytest tests/ -v --timeout=60
```

If you are changing behavior in one subsystem, it is worth running the narrowest relevant tests first, then the broader suite. For example:

| Change area | Suggested tests |
|---|---|
| CLI flags / command registration | `go test ./... -run TestRootCommandHasSubcommands` |
| Hook install/uninstall | `go test ./... -run TestHookInstall` |
| Analysis / refactor detection | `go test ./... -run TestDetectAll` |
| Server routes and rendering | `go test ./... -run TestAPIGraph` |
| Storage migrations / persistence | `go test ./... -run TestOpenAndClose` |
| Python extraction / orchestration | `pytest tests/test_multilang_extractors.py` or related focused tests |

The Go test suite also has strong unit coverage for core modules like [`DetectAll`](go/internal/analysis/refactor_detector.go#L404), [`RunAsk`](go/internal/orchestrator/run_ask.go#L59), [`RunDigest`](go/internal/orchestrator/run_digest.go#L48), [`Snapshotter.Snapshot`](go/internal/orchestrator/snapshotter.go#L89), and [`Store.Open`](go/internal/storage/store.go#L24).

> **Sources:** `test_commands` · `go/cmd/rekipedia/cmd/root_test.go` · L19–L29 · [`TestRootCommandHasSubcommands`](go/cmd/rekipedia/cmd/root_test.go#L19) · `go/cmd/rekipedia/cmd/hook_test.go` · L20–L50 · [`TestHookInstall`](go/cmd/rekipedia/cmd/hook_test.go#L20) · `go/internal/analysis/refactor_detector.go` · L404–L413 · [`DetectAll`](go/internal/analysis/refactor_detector.go#L404) · `go/internal/orchestrator/run_ask.go` · L59–L109 · [`RunAsk`](go/internal/orchestrator/run_ask.go#L59) · `go/internal/orchestrator/run_digest.go` · L48–L309 · [`RunDigest`](go/internal/orchestrator/run_digest.go#L48) · `go/internal/orchestrator/snapshotter.go` · L89–L147 · [`Snapshotter`](go/internal/orchestrator/snapshotter.go#L57) · `go/internal/storage/store.go` · L24–L35 · [`Open`](go/internal/storage/store.go#L24)

## Formatting and Linting

The repo uses dedicated formatting and linting configuration files, which means contributor changes should follow the project’s existing style rather than introducing new conventions.

### Python formatting

The Python side is configured through:

- `.ruff_cache/` metadata in the repo snapshot
- `pyproject.toml`
- `uv.lock`

Although the exact formatter/linter commands are not explicitly listed in the analysis payload, the presence of `pyproject.toml` and `uv.lock` indicates Python tooling is managed centrally. In practice, contributors should keep Python edits aligned with the project’s configured formatter and linter expectations before running the test suite.

### Go linting and style

The Go subtree has its own linting and style configuration:

- `.golangci.yml`
- `checkstyle.xml`
- `pmd-ruleset.xml`

The Go build command to validate compile-time correctness is:

```bash
CGO_ENABLED=0 go build -ldflags "-s -w" -o /tmp/reki ./cmd/rekipedia
```

If your change touches public-facing APIs or packages used across modules, make sure the code still passes the Go tests because many style and structure issues are caught there as well.

### JS / TypeScript formatting

The Node entrypoint and build script are minimal, but the repository includes:

```bash
npm run build  # tsc
```

That indicates the JavaScript/TypeScript surface is validated by TypeScript compilation. If you touch `bin/rekipedia.js` or related JS/TS support code, run the build command to confirm there are no type or syntax issues.

### Repo-enforced workflow files

For automated enforcement, the repository also contains:

- `.pre-commit-config.yaml`
- `.prettierrc.json`
- `.eslintrc.json`

These files suggest contributors should prefer the existing hooks and formatter rules rather than ad hoc local conventions.

> **Sources:** `pyproject.toml` · `uv.lock` · `.pre-commit-config.yaml` · `.prettierrc.json` · `.eslintrc.json` · `.golangci.yml` · `checkstyle.xml` · `pmd-ruleset.xml` · `bin/rekipedia.js` · L4–L4 · [`tryRun`](bin/rekipedia.js#L4)

## Submitting Changes

Changes should be validated against the repository’s established workflow before you open a PR:

1. Run the relevant test command for the area you changed.
2. Run the applicable build/compile command.
3. Verify the repo-specific formatting/linting rules.
4. Check that the change fits the existing command structure and module boundaries.

For Go changes, that usually means:

```bash
go test ./... -v -count=1 -timeout 120s
CGO_ENABLED=0 go build -ldflags "-s -w" -o /tmp/reki ./cmd/rekipedia
```

For Python changes, the repo’s baseline validation is:

```bash
pytest
uv build
```

For TypeScript/JS changes:

```bash
npm run build  # tsc
```

The contributor-facing docs in `CONTRIBUTING.md` and the Go subtree docs in `go/README.md` should be treated as the authoritative workflow references, but the concrete validation steps above are what the repository actually encodes in its tooling.

### PR readiness checklist

Use this as a concise pre-PR gate:

- [ ] Relevant unit/integration tests passed for the touched area
- [ ] Broader suite passed if the change spans multiple modules
- [ ] Python build completed with `uv build`
- [ ] Go build completed with `CGO_ENABLED=0 go build -ldflags "-s -w" -o /tmp/reki ./cmd/rekipedia`
- [ ] TypeScript build completed with `npm run build  # tsc` if JS/TS files changed
- [ ] Formatting/linting completed using the repo’s configured tooling
- [ ] No accidental changes to generated outputs or fixtures
- [ ] CLI/help or server behavior still matches the existing tests

### Suggested review focus

When reviewing your own patch, confirm that it remains consistent with the existing test coverage in areas such as:

- command registration in [`Execute`](go/cmd/rekipedia/cmd/root.go#L44)
- configuration loading in [`Load`](go/internal/config/loader.go#L55)
- extraction in [`Registry.ExtractFile`](go/internal/extractor/extractor.go#L37)
- orchestration in [`RunUpdate`](go/internal/orchestrator/run_update.go#L30)
- persistence in [`Store.SaveSymbols`](go/internal/storage/store.go#L149)

That keeps the contribution aligned with the repo’s established workflows rather than introducing new ones.

> **Sources:** `CONTRIBUTING.md` · `go/README.md` · `go/cmd/rekipedia/cmd/root.go` · L44–L48 · [`Execute`](go/cmd/rekipedia/cmd/root.go#L44) · `go/internal/config/loader.go` · L55–L66 · [`Load`](go/internal/config/loader.go#L55) · `go/internal/extractor/extractor.go` · L37–L47 · [`(r *Registry).ExtractFile`](go/internal/extractor/extractor.go#L37) · `go/internal/orchestrator/run_update.go` · L30–L179 · [`RunUpdate`](go/internal/orchestrator/run_update.go#L30) · `go/internal/storage/store.go` · L149–L171 · [`(s *Store).SaveSymbols`](go/internal/storage/store.go#L149)