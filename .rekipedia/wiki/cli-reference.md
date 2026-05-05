---
slug: cli-reference
title: "CLI Reference"
section: api-reference
tags: [api, cli, reference]
pin: false
importance: 50
created_at: 2026-05-05T04:25:26Z
rekipedia_version: 0.10.2
---

# CLI Reference

This page is a practical command-by-command reference for the user-facing `rekipedia` CLI. It is organized by the root command and its subcommands, with usage, flags, examples, and exit behavior. It focuses on the command package in `go/cmd/rekipedia/cmd` and the entrypoint in [`main`](go/cmd/rekipedia/main.go#L6) / [`Execute`](go/cmd/rekipedia/cmd/root.go#L44). It intentionally avoids broader architecture discussion.

## Root Command: `rekipedia`

The root command is defined in [`Execute`](go/cmd/rekipedia/cmd/root.go#L44-L48) and initialized in [`init`](go/cmd/rekipedia/cmd/root.go#L50-L77). The root also prints the banner via [`printRootBanner`](go/cmd/rekipedia/cmd/root.go#L36-L41). The CLI entrypoint simply calls [`Execute`](go/cmd/rekipedia/cmd/root.go#L44-L48) from [`main`](go/cmd/rekipedia/main.go#L6-L8).

### Usage

The exact root usage string is defined by the Cobra command in [`root.go`](go/cmd/rekipedia/cmd/root.go#L50-L77). At the top level, the CLI serves as a dispatcher for subcommands such as `ask`, `scan`, `serve`, `update`, `hook`, `embed`, `export`, `refactor`, `search`, `diff`, `impact`, and `context`.

### Flags

The root command includes the version flag, which is covered by [`TestRootVersionFlag`](go/cmd/rekipedia/cmd/root_test.go#L9-L17). The test confirms the root command exposes version output and that the root command has registered subcommands via [`TestRootCommandHasSubcommands`](go/cmd/rekipedia/cmd/root_test.go#L19-L29).

### Examples

```bash
rekipedia --version
rekipedia <subcommand> [flags]
```

### Exit Behavior

- Success: the command exits `0`.
- Version/help requests: exit `0`.
- Root-level initialization errors propagate from [`Execute`](go/cmd/rekipedia/cmd/root.go#L44-L48) and result in a non-zero exit code.

> **Sources:** `go/cmd/rekipedia/main.go` · L6–L8 · [`main`](go/cmd/rekipedia/main.go#L6)  
> **Sources:** `go/cmd/rekipedia/cmd/root.go` · L36–L77 · [`printRootBanner`](go/cmd/rekipedia/cmd/root.go#L36) · [`Execute`](go/cmd/rekipedia/cmd/root.go#L44)

## Command Table

| Command | Purpose | Key flags observed in analysis | Defined in |
|---|---|---|---|
| `rekipedia` | Root dispatcher | version flag | [`root.go`](go/cmd/rekipedia/cmd/root.go#L50-L77) |
| `ask` | Interactive / question answering | not fully enumerated in symbols; interactive runner exists | [`ask.go`](go/cmd/rekipedia/cmd/ask.go#L77-L174) |
| `context` | Context normalization / title formatting utilities | not fully enumerated in symbols | [`context.go`](go/cmd/rekipedia/cmd/context.go#L109-L123) |
| `diff` | Diff generation from symbol JSON | not fully enumerated in symbols | [`diff.go`](go/cmd/rekipedia/cmd/diff.go#L119-L260) |
| `embed` | Generate embeddings | tests confirm flags and registration | [`embed.go`](go/cmd/rekipedia/cmd/embed.go#L56-L63) |
| `export` | Export generated artifacts | tests confirm flags and registration | [`export.go`](go/cmd/rekipedia/cmd/export.go#L101-L105) |
| `hook` | Git hook installation/status | tests confirm install/uninstall/status behavior | [`hook.go`](go/cmd/rekipedia/cmd/hook.go#L79-L82) |
| `impact` | Impact/priority analysis | symbol `qitem` indicates internal queueing | [`impact.go`](go/cmd/rekipedia/cmd/impact.go#L62-L65) |
| `init` | Initialize config/workspace files | command init function exists | [`init.go`](go/cmd/rekipedia/cmd/init.go#L62-L64) |
| `refactor` | Static refactor issue detection/reporting | flags and use line verified by tests | [`refactor.go`](go/cmd/rekipedia/cmd/refactor.go#L57-L305) |
| `scan` | Scan repository and prepare LLM config | config-loading helpers and language splitting | [`scan.go`](go/cmd/rekipedia/cmd/scan.go#L128-L180) |
| `search` | Search indexed symbols | BM25 tokenizer and result type | [`search.go`](go/cmd/rekipedia/cmd/search.go#L20-L102) |
| `serve` | Serve web/API UI | banner + server startup setup | [`serve.go`](go/cmd/rekipedia/cmd/serve.go#L29-L84) |
| `update` | Refresh generated data | update command init exists | [`update.go`](go/cmd/rekipedia/cmd/update.go#L47-L53) |
| `watch` | Watch files/config for changes | watch config helpers and command init | [`watch.go`](go/cmd/rekipedia/cmd/watch.go#L14-L123) |

> **Sources:** `go/cmd/rekipedia/cmd/root.go` · L50–L77 · [`Execute`](go/cmd/rekipedia/cmd/root.go#L44)  
> **Sources:** `go/cmd/rekipedia/cmd/refactor.go` · L57–L305 · [`Finding`](go/cmd/rekipedia/cmd/refactor.go#L57) · [`buildStaticReport`](go/cmd/rekipedia/cmd/refactor.go#L148)

## `ask`

[`runInteractiveAsk`](go/cmd/rekipedia/cmd/ask.go#L87-L174) implements the interactive ask flow, while [`init`](go/cmd/rekipedia/cmd/ask.go#L77-L84) registers the command. This command is part of the user-facing Q&A path.

### Usage

The command is wired through Cobra in [`ask.go`](go/cmd/rekipedia/cmd/ask.go#L77-L174). The observed implementation indicates an interactive prompt/session model, not a simple batch-only subcommand.

### Flags

The analysis shows the command exists and is registered, but the exact flag list is not fully exposed in symbol metadata. The implementation depends on the orchestration layer via [`RunAsk`](go/internal/orchestrator/run_ask.go#L59-L109) and [`StreamAsk`](go/internal/orchestrator/run_ask.go#L112-L140).

### Examples

```bash
rekipedia ask
rekipedia ask --help
```

### Exit Behavior

- If the interactive session completes normally, exit `0`.
- Input, context, or downstream orchestration errors propagate from the interactive runner and should produce a non-zero exit.

> **Sources:** `go/cmd/rekipedia/cmd/ask.go` · L77–L174 · [`runInteractiveAsk`](go/cmd/rekipedia/cmd/ask.go#L87)  
> **Sources:** `go/internal/orchestrator/run_ask.go` · L59–L140 · [`RunAsk`](go/internal/orchestrator/run_ask.go#L59) · [`StreamAsk`](go/internal/orchestrator/run_ask.go#L112)

## `scan`

[`loadLLMConfig`](go/cmd/rekipedia/cmd/scan.go#L143-L161) and [`splitLanguages`](go/cmd/rekipedia/cmd/scan.go#L165-L180) are the primary observable helpers behind the scan command. The command registration lives in [`init`](go/cmd/rekipedia/cmd/scan.go#L128-L140).

### Usage

`scan` is the repository analysis entrypoint. Based on the helper functions and test coverage in [`TestLoadLLMConfig`](go/cmd/rekipedia/cmd/root_test.go#L91-L102) and [`TestSplitLanguages`](go/cmd/rekipedia/cmd/root_test.go#L66-L89), it accepts configuration-related options and supports language-list parsing.

### Flags

The analysis data does not expose the full flag list, but the command clearly relies on:
- LLM configuration loading via [`loadLLMConfig`](go/cmd/rekipedia/cmd/scan.go#L143-L161)
- Language parsing via [`splitLanguages`](go/cmd/rekipedia/cmd/scan.go#L165-L180)

### Examples

```bash
rekipedia scan
rekipedia scan --help
```

### Exit Behavior

- Successful scan and configuration load: exit `0`.
- Misconfiguration or invalid language/config input: non-zero exit.
- The helper [`loadLLMConfig`](go/cmd/rekipedia/cmd/scan.go#L143-L161) suggests failure modes around invalid or absent LLM configuration.

> **Sources:** `go/cmd/rekipedia/cmd/scan.go` · L128–L180 · [`loadLLMConfig`](go/cmd/rekipedia/cmd/scan.go#L143) · [`splitLanguages`](go/cmd/rekipedia/cmd/scan.go#L165)

## `serve`

[`printServeBanner`](go/cmd/rekipedia/cmd/serve.go#L29-L51) and [`init`](go/cmd/rekipedia/cmd/serve.go#L78-L84) define the command behavior and registration.

### Usage

`serve` starts the HTTP server. It is associated with the server implementation in [`New`](go/internal/server/server.go#L46-L48) and [`(s *Server).Start`](go/internal/server/server.go#L71-L96).

### Flags

The symbol data does not enumerate individual flags for `serve`. However, the server startup is clearly a configurable CLI entrypoint.

### Examples

```bash
rekipedia serve
rekipedia serve --help
```

### Exit Behavior

- Server starts successfully and keeps running: exit only when interrupted or when startup fails.
- Startup failures from the underlying server should produce a non-zero exit.

> **Sources:** `go/cmd/rekipedia/cmd/serve.go` · L29–L84 · [`printServeBanner`](go/cmd/rekipedia/cmd/serve.go#L29)  
> **Sources:** `go/internal/server/server.go` · L46–L96 · [`New`](go/internal/server/server.go#L46) · [`(s *Server).Start`](go/internal/server/server.go#L71)

## `update`, `export`, `embed`, `refactor`, `hook`, `search`, `diff`, `impact`, `context`, `init`, `watch`

These commands are registered in the command package, but the symbol metadata only partially exposes their flag sets. The table below summarizes what can be confirmed from the analysis.

| Subcommand | Confirmed behavior from symbols | Practical note |
|---|---|---|
| `update` | registered in [`update.go`](go/cmd/rekipedia/cmd/update.go#L47-L53) | refresh/update workflow |
| `export` | tests verify registration and default format in [`TestExportCmdDefaultFormat`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L71-L79) | produces export artifacts |
| `embed` | tests verify registration, flags, and use line in [`TestEmbedCmdFlags`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L30-L37) | generates embeddings |
| `refactor` | static analysis/reporting with [`Finding`](go/cmd/rekipedia/cmd/refactor.go#L57-L63), [`staticWalk`](go/cmd/rekipedia/cmd/refactor.go#L75-L127), [`buildStaticReport`](go/cmd/rekipedia/cmd/refactor.go#L148-L175) | supports `--json`/report output by test coverage |
| `hook` | tests cover install, uninstall, status | manages Git hook integration |
| `search` | uses [`tokenizeSymbol`](go/cmd/rekipedia/cmd/search.go#L20-L51) and [`scoreBM25`](go/cmd/rekipedia/cmd/search.go#L54-L71) | symbol search |
| `diff` | formats Markdown/text diffs from changed symbols | diff output for code changes |
| `impact` | contains [`qitem`](go/cmd/rekipedia/cmd/impact.go#L62-L65) | likely prioritization/impact ranking |
| `context` | contains [`toTitle`](go/cmd/rekipedia/cmd/context.go#L109-L117) | title/context formatting |
| `init` | init command registered | initializes project files/config |
| `watch` | uses [`watchConfig`](go/cmd/rekipedia/cmd/watch.go#L14-L16), [`loadWatchConfig`](go/cmd/rekipedia/cmd/watch.go#L18-L26), [`saveWatchConfig`](go/cmd/rekipedia/cmd/watch.go#L28-L35) | watches and persists config |

### Examples

```bash
rekipedia update
rekipedia export --help
rekipedia embed --help
rekipedia refactor --json
rekipedia hook install
rekipedia search "symbol name"
rekipedia diff
rekipedia watch
```

### Exit Behavior

The most reliable exit behavior is command-specific:
- `export`, `embed`, `refactor`, `search`, and `diff` should return non-zero on file I/O or parse failures.
- `hook` should return non-zero if repository or Git hook state is invalid.
- `watch` generally runs until interrupted and exits non-zero if setup fails.

> **Sources:** `go/cmd/rekipedia/cmd/update.go` · L47–L53 · [`init`](go/cmd/rekipedia/cmd/update.go#L47)  
> **Sources:** `go/cmd/rekipedia/cmd/embed_export_update_test.go` · L17–L166 · [`TestEmbedCmdRegistered`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L17) · [`TestExportCmdDefaultFormat`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L71) · [`TestUpdateCmdUseLine`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L107)  
> **Sources:** `go/cmd/rekipedia/cmd/refactor.go` · L57–L305 · [`staticWalk`](go/cmd/rekipedia/cmd/refactor.go#L75) · [`buildStaticReport`](go/cmd/rekipedia/cmd/refactor.go#L148)

## Flag Reference

The analysis data does not expose a complete authoritative flag inventory for every command, so the table below is limited to flags that are indirectly confirmed by tests or helper functions.

| Command | Flag / option | Evidence | Behavior |
|---|---|---|---|
| `refactor` | `--json` | [`TestRefactorJSONWritesFile`](go/cmd/rekipedia/cmd/refactor_test.go#L269-L301) | writes JSON output instead of only text/report output |
| `refactor` | `--with-refactor` (scan-related flag) | [`TestScanHasWithRefactorFlag`](go/cmd/rekipedia/cmd/refactor_test.go#L307-L312) | scan integrates refactor analysis |
| `embed` | flags present | [`TestEmbedCmdFlags`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L30-L37) | exact set not enumerated in symbols |
| `export` | flags present | [`TestExportCmdFlags`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L62-L69) | exact set not enumerated in symbols |
| `update` | flags present | [`TestUpdateCmdFlags`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L98-L105) | exact set not enumerated in symbols |

### Notes on incomplete flag visibility

The static analysis payload provides registration and test evidence, but not the full Cobra flag definitions for all commands. Where flag names are not directly visible in symbols, this page avoids inventing them.

> **Sources:** `go/cmd/rekipedia/cmd/refactor_test.go` · L269–L312 · [`TestRefactorJSONWritesFile`](go/cmd/rekipedia/cmd/refactor_test.go#L269) · [`TestScanHasWithRefactorFlag`](go/cmd/rekipedia/cmd/refactor_test.go#L307)  
> **Sources:** `go/cmd/rekipedia/cmd/embed_export_update_test.go` · L30–L105 · [`TestEmbedCmdFlags`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L30) · [`TestExportCmdFlags`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L62) · [`TestUpdateCmdFlags`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L98)

## Practical Exit-Code Expectations

Across the CLI, exit behavior generally follows a simple pattern:

| Scenario | Expected exit |
|---|---|
| Help/version output | `0` |
| Successful command execution | `0` |
| Invalid flags or command syntax | non-zero |
| Missing files/config/repo state | non-zero |
| Long-running server/watch commands started successfully | process remains running until stopped |

This is inferred from the command registration and the test suite’s focus on failure modes, especially for `root`, `hook`, `refactor`, and `scan`.

> **Sources:** `go/cmd/rekipedia/cmd/root_test.go` · L9–L29 · [`TestRootVersionFlag`](go/cmd/rekipedia/cmd/root_test.go#L9)  
> **Sources:** `go/cmd/rekipedia/cmd/hook_test.go` · L20–L114 · [`TestHookInstall`](go/cmd/rekipedia/cmd/hook_test.go#L20) · [`TestHookStatusNotInstalled`](go/cmd/rekipedia/cmd/hook_test.go#L106)  
> **Sources:** `go/cmd/rekipedia/cmd/refactor_test.go` · L65–L312 · [`TestStaticWalkFindsTODO`](go/cmd/rekipedia/cmd/refactor_test.go#L65) · [`TestRefactorJSONWritesFile`](go/cmd/rekipedia/cmd/refactor_test.go#L269)