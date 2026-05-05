---
slug: go-api
title: "Go Command Tree and Package Surface Reference"
section: api-reference
tags: [api, reference]
pin: false
importance: 50
created_at: 2026-05-05T04:25:37Z
rekipedia_version: 0.10.2
---

# Go Command Tree and Package Surface Reference

## Overview

This page documents the **Go package surface that defines the application interface**: the command tree under `go/cmd/rekipedia/cmd`, the `main` entry point, and the shared packages that those commands depend on. It is intentionally focused on the exported and user-facing surface area, rather than the full architecture or installation story.

The CLI entry point is the [`main`](go/cmd/rekipedia/main.go#L6) function in [`go/cmd/rekipedia/main.go`](go/cmd/rekipedia/main.go#L6-L8), which delegates to [`Execute`](go/cmd/rekipedia/cmd/root.go#L44) in [`go/cmd/rekipedia/cmd/root.go`](go/cmd/rekipedia/cmd/root.go#L44-L48). From there, the command tree is assembled via `init()` functions spread across subcommand files such as [`ask.go`](go/cmd/rekipedia/cmd/ask.go#L77), [`scan.go`](go/cmd/rekipedia/cmd/scan.go#L128), [`serve.go`](go/cmd/rekipedia/cmd/serve.go#L78), and others. This package layout is conventional for Cobra-style CLI registration, with the root command owning global flags and each subcommand file contributing its own `init()` registration.

At a higher level, the command packages are the interface layer over shared subsystems:
- [`go/internal/orchestrator`](go/internal/orchestrator/run_ask.go#L59) implements end-to-end actions like ask, digest, scan, and update.
- [`go/internal/extractor`](go/internal/extractor/extractor.go#L11) provides language/file parsing primitives.
- [`go/internal/rag`](go/internal/rag/chunker.go#L40) provides chunking, embeddings, and scan metadata storage.
- [`go/internal/storage`](go/internal/storage/store.go#L24) persists runs, symbols, relationships, pages, QA history, and manifests.
- [`go/internal/llm`](go/internal/llm/client.go#L120) wraps model calls and embeddings.
- [`go/internal/models`](go/internal/models/contracts.go#L6) defines the shared contracts passed across layers.

This page includes a reference table of important symbols and a breakdown of how the command subpackages are organized.

> **Sources:** `go/cmd/rekipedia/main.go` · L6–L8 · [`main`](go/cmd/rekipedia/main.go#L6)  
> **Sources:** `go/cmd/rekipedia/cmd/root.go` · L44–L77 · [`Execute`](go/cmd/rekipedia/cmd/root.go#L44), [`init`](go/cmd/rekipedia/cmd/root.go#L50)  
> **Sources:** `go/internal/orchestrator/run_ask.go` · L59–L261 · [`RunAsk`](go/internal/orchestrator/run_ask.go#L59), [`buildContext`](go/internal/orchestrator/run_ask.go#L211)  

## Command Tree Organization

The CLI is organized around a root command plus focused subcommands, each in its own file under `go/cmd/rekipedia/cmd`. The analysis data shows a clear pattern: each subcommand file uses an `init()` function to register itself and wire flags.

### Root command

[`root.go`](go/cmd/rekipedia/cmd/root.go#L36-L77) provides the main command entry and global setup:
- [`printRootBanner`](go/cmd/rekipedia/cmd/root.go#L36-L41) handles startup messaging.
- [`Execute`](go/cmd/rekipedia/cmd/root.go#L44-L48) is the canonical entry used by `main`.
- [`init`](go/cmd/rekipedia/cmd/root.go#L50-L77) sets up the root command, subcommand registration, and shared flags.

Tests confirm the root command is expected to expose subcommands and version behavior via [`TestRootVersionFlag`](go/cmd/rekipedia/cmd/root_test.go#L9-L17) and [`TestRootCommandHasSubcommands`](go/cmd/rekipedia/cmd/root_test.go#L19-L29).

### User interaction and query commands

The command tree contains a set of user-facing flows:
- [`ask.go`](go/cmd/rekipedia/cmd/ask.go#L77-L174) includes [`runInteractiveAsk`](go/cmd/rekipedia/cmd/ask.go#L87-L174), suggesting an interactive prompt-based mode.
- [`search.go`](go/cmd/rekipedia/cmd/search.go#L20-L142) defines local symbol scoring helpers like [`tokenizeSymbol`](go/cmd/rekipedia/cmd/search.go#L20-L51) and [`scoreBM25`](go/cmd/rekipedia/cmd/search.go#L54-L71).
- [`serve.go`](go/cmd/rekipedia/cmd/serve.go#L29-L84) includes [`printServeBanner`](go/cmd/rekipedia/cmd/serve.go#L29-L51) and registers the server-facing command.
- [`watch.go`](go/cmd/rekipedia/cmd/watch.go#L14-L123) manages persisted watch settings through [`watchConfig`](go/cmd/rekipedia/cmd/watch.go#L14-L16), [`loadWatchConfig`](go/cmd/rekipedia/cmd/watch.go#L18-L26), and [`saveWatchConfig`](go/cmd/rekipedia/cmd/watch.go#L28-L35).

### Analysis and maintenance commands

The more analysis-oriented subcommands are also split cleanly:
- [`scan.go`](go/cmd/rekipedia/cmd/scan.go#L128-L180) provides config loading helpers such as [`loadLLMConfig`](go/cmd/rekipedia/cmd/scan.go#L143-L161) and [`splitLanguages`](go/cmd/rekipedia/cmd/scan.go#L165-L180).
- [`digest.go`](go/cmd/rekipedia/cmd/diff.go#L119-L260) includes diff/report formatting helpers like [`formatDiffMd`](go/cmd/rekipedia/cmd/diff.go#L175-L214) and [`formatDiffText`](go/cmd/rekipedia/cmd/diff.go#L216-L252).
- [`refactor.go`](go/cmd/rekipedia/cmd/refactor.go#L57-L305) implements static issue detection support with [`Finding`](go/cmd/rekipedia/cmd/refactor.go#L57-L63), [`staticWalk`](go/cmd/rekipedia/cmd/refactor.go#L75-L127), and [`buildStaticReport`](go/cmd/rekipedia/cmd/refactor.go#L148-L175).
- [`update.go`](go/cmd/rekipedia/cmd/update.go#L47-L53) registers update behavior.
- [`embed.go`](go/cmd/rekipedia/cmd/embed.go#L56-L63) registers the embed subcommand.
- [`hook.go`](go/cmd/rekipedia/cmd/hook.go#L79-L82) registers the git-hook management command.
- [`context.go`](go/cmd/rekipedia/cmd/context.go#L109-L123) includes [`toTitle`](go/cmd/rekipedia/cmd/context.go#L109-L117), a shared formatting helper.

#### Command file organization at a glance

| File | Responsibility | Notable symbols |
|---|---|---|
| `go/cmd/rekipedia/cmd/root.go` | Root command and global setup | [`Execute`](go/cmd/rekipedia/cmd/root.go#L44), [`printRootBanner`](go/cmd/rekipedia/cmd/root.go#L36) |
| `go/cmd/rekipedia/cmd/ask.go` | Interactive ask flow | [`runInteractiveAsk`](go/cmd/rekipedia/cmd/ask.go#L87) |
| `go/cmd/rekipedia/cmd/scan.go` | Config loading and scan setup | [`loadLLMConfig`](go/cmd/rekipedia/cmd/scan.go#L143), [`splitLanguages`](go/cmd/rekipedia/cmd/scan.go#L165) |
| `go/cmd/rekipedia/cmd/search.go` | Search scoring helpers | [`tokenizeSymbol`](go/cmd/rekipedia/cmd/search.go#L20), [`scoreBM25`](go/cmd/rekipedia/cmd/search.go#L54) |
| `go/cmd/rekipedia/cmd/refactor.go` | Static refactor analysis command | [`Finding`](go/cmd/rekipedia/cmd/refactor.go#L57), [`staticWalk`](go/cmd/rekipedia/cmd/refactor.go#L75) |
| `go/cmd/rekipedia/cmd/diff.go` | Diff-based reporting | [`formatDiffMd`](go/cmd/rekipedia/cmd/diff.go#L175), [`formatDiffText`](go/cmd/rekipedia/cmd/diff.go#L216) |
| `go/cmd/rekipedia/cmd/watch.go` | Watch configuration persistence | [`watchConfig`](go/cmd/rekipedia/cmd/watch.go#L14), [`loadWatchConfig`](go/cmd/rekipedia/cmd/watch.go#L18) |

> **Sources:** `go/cmd/rekipedia/cmd/root.go` · L36–L77 · [`printRootBanner`](go/cmd/rekipedia/cmd/root.go#L36), [`Execute`](go/cmd/rekipedia/cmd/root.go#L44), [`init`](go/cmd/rekipedia/cmd/root.go#L50)  
> **Sources:** `go/cmd/rekipedia/cmd/ask.go` · L77–L174 · [`runInteractiveAsk`](go/cmd/rekipedia/cmd/ask.go#L87)  
> **Sources:** `go/cmd/rekipedia/cmd/refactor.go` · L57–L305 · [`Finding`](go/cmd/rekipedia/cmd/refactor.go#L57), [`staticWalk`](go/cmd/rekipedia/cmd/refactor.go#L75), [`buildStaticReport`](go/cmd/rekipedia/cmd/refactor.go#L148)  

## Key Exported Types and Functions

The most important exported API surface lives in shared internal packages rather than the `cmd` package itself. The command layer mainly wires user input to these reusable building blocks.

### Core entry points

| Symbol | File | Role |
|---|---|---|
| [`main`](go/cmd/rekipedia/main.go#L6) | `go/cmd/rekipedia/main.go` | Process entry point |
| [`Execute`](go/cmd/rekipedia/cmd/root.go#L44) | `go/cmd/rekipedia/cmd/root.go` | Root command runner |
| [`RunAsk`](go/internal/orchestrator/run_ask.go#L59) | `go/internal/orchestrator/run_ask.go` | Ask flow orchestration |
| [`RunDigest`](go/internal/orchestrator/run_digest.go#L48) | `go/internal/orchestrator/run_digest.go` | Digest/report orchestration |
| [`RunUpdate`](go/internal/orchestrator/run_update.go#L30) | `go/internal/orchestrator/run_update.go` | Update workflow |
| [`WriteRefactorOutputs`](go/internal/analysis/refactor_writer.go#L269) | `go/internal/analysis/refactor_writer.go` | Emits refactor report artifacts |

### Shared data contracts

`go/internal/models/contracts.go` defines the data structures passed between command and subsystem layers:
- [`LLMConfig`](go/internal/models/contracts.go#L6-L15) and [`DefaultLLMConfig`](go/internal/models/contracts.go#L18-L23)
- [`Symbol`](go/internal/models/contracts.go#L53-L61)
- [`Relationship`](go/internal/models/contracts.go#L64-L71)
- [`RationaleNote`](go/internal/models/contracts.go#L74-L79)
- [`AnalysisResult`](go/internal/models/contracts.go#L82-L94)
- [`Shard`](go/internal/models/contracts.go#L97-L101)
- [`QAHistory`](go/internal/models/contracts.go#L104-L108)
- [`FileManifest`](go/internal/models/contracts.go#L111-L116)
- [`WikiPageSpec`](go/internal/models/contracts.go#L119-L129)
- [`WikiSection`](go/internal/models/contracts.go#L132-L136)
- [`WikiPlan`](go/internal/models/contracts.go#L139-L144)
- [`ScanMeta`](go/internal/models/contracts.go#L147-L156)

These types are the canonical interface between the CLI, storage, analysis, and page synthesis layers.

### Shared helpers used by command flows

A few helpers are worth calling out because they are reused indirectly by several commands:
- [`loadLLMConfig`](go/cmd/rekipedia/cmd/scan.go#L143-L161) and [`splitLanguages`](go/cmd/rekipedia/cmd/scan.go#L165-L180) shape scan configuration.
- [`toTitle`](go/cmd/rekipedia/cmd/context.go#L109-L117) normalizes display labels.
- [`symbolKey`](go/cmd/rekipedia/cmd/diff.go#L149-L157) and [`isInChangedFiles`](go/cmd/rekipedia/cmd/diff.go#L159-L173) help diff reports correlate symbols with file changes.
- [`tokenizeSymbol`](go/cmd/rekipedia/cmd/search.go#L20-L51) and [`scoreBM25`](go/cmd/rekipedia/cmd/search.go#L54-L71) support CLI search ranking.
- [`finishDigest`](go/internal/orchestrator/helpers.go#L18-L91) is a shared orchestration helper for digest completion logic.

> **Sources:** `go/cmd/rekipedia/main.go` · L6–L8 · [`main`](go/cmd/rekipedia/main.go#L6)  
> **Sources:** `go/cmd/rekipedia/cmd/root.go` · L44–L48 · [`Execute`](go/cmd/rekipedia/cmd/root.go#L44)  
> **Sources:** `go/internal/models/contracts.go` · L6–L156 · [`LLMConfig`](go/internal/models/contracts.go#L6), [`Symbol`](go/internal/models/contracts.go#L53), [`WikiPlan`](go/internal/models/contracts.go#L139)  
> **Sources:** `go/cmd/rekipedia/cmd/scan.go` · L143–L180 · [`loadLLMConfig`](go/cmd/rekipedia/cmd/scan.go#L143), [`splitLanguages`](go/cmd/rekipedia/cmd/scan.go#L165)  
> **Sources:** `go/cmd/rekipedia/cmd/diff.go` · L149–L252 · [`symbolKey`](go/cmd/rekipedia/cmd/diff.go#L149), [`formatDiffMd`](go/cmd/rekipedia/cmd/diff.go#L175)  
> **Sources:** `go/internal/orchestrator/helpers.go` · L18–L91 · [`finishDigest`](go/internal/orchestrator/helpers.go#L18)  

## Important Symbols Table

This table highlights the most relevant symbols shaping the application interface, with direct file references for traceability.

| Symbol | Kind | File |
|---|---|---|
| [`main`](go/cmd/rekipedia/main.go#L6) | function | `go/cmd/rekipedia/main.go` |
| [`Execute`](go/cmd/rekipedia/cmd/root.go#L44) | function | `go/cmd/rekipedia/cmd/root.go` |
| [`runInteractiveAsk`](go/cmd/rekipedia/cmd/ask.go#L87) | function | `go/cmd/rekipedia/cmd/ask.go` |
| [`loadLLMConfig`](go/cmd/rekipedia/cmd/scan.go#L143) | function | `go/cmd/rekipedia/cmd/scan.go` |
| [`splitLanguages`](go/cmd/rekipedia/cmd/scan.go#L165) | function | `go/cmd/rekipedia/cmd/scan.go` |
| [`tokenizeSymbol`](go/cmd/rekipedia/cmd/search.go#L20) | function | `go/cmd/rekipedia/cmd/search.go` |
| [`scoreBM25`](go/cmd/rekipedia/cmd/search.go#L54) | function | `go/cmd/rekipedia/cmd/search.go` |
| [`Finding`](go/cmd/rekipedia/cmd/refactor.go#L57) | type | `go/cmd/rekipedia/cmd/refactor.go` |
| [`staticWalk`](go/cmd/rekipedia/cmd/refactor.go#L75) | function | `go/cmd/rekipedia/cmd/refactor.go` |
| [`buildStaticReport`](go/cmd/rekipedia/cmd/refactor.go#L148) | function | `go/cmd/rekipedia/cmd/refactor.go` |
| [`watchConfig`](go/cmd/rekipedia/cmd/watch.go#L14) | type | `go/cmd/rekipedia/cmd/watch.go` |
| [`loadWatchConfig`](go/cmd/rekipedia/cmd/watch.go#L18) | function | `go/cmd/rekipedia/cmd/watch.go` |
| [`saveWatchConfig`](go/cmd/rekipedia/cmd/watch.go#L28) | function | `go/cmd/rekipedia/cmd/watch.go` |
| [`RunAsk`](go/internal/orchestrator/run_ask.go#L59) | function | `go/internal/orchestrator/run_ask.go` |
| [`RunDigest`](go/internal/orchestrator/run_digest.go#L48) | function | `go/internal/orchestrator/run_digest.go` |
| [`RunUpdate`](go/internal/orchestrator/run_update.go#L30) | function | `go/internal/orchestrator/run_update.go` |
| [`ShardPlanner`](go/internal/orchestrator/sharding.go#L17) | type | `go/internal/orchestrator/sharding.go` |
| [`Snapshotter`](go/internal/orchestrator/snapshotter.go#L57) | type | `go/internal/orchestrator/snapshotter.go` |
| [`Store`](go/internal/storage/store.go#L18) | type | `go/internal/storage/store.go` |
| [`Client`](go/internal/llm/client.go#L110) | type | `go/internal/llm/client.go` |
| [`Symbol`](go/internal/models/contracts.go#L53) | type | `go/internal/models/contracts.go` |
| [`WikiPlan`](go/internal/models/contracts.go#L139) | type | `go/internal/models/contracts.go` |
| [`PageBuilder`](go/internal/synthesis/page_builder.go#L60) | type | `go/internal/synthesis/page_builder.go` |
| [`DiagramBuilder`](go/internal/synthesis/diagram_builder.go#L16) | type | `go/internal/synthesis/diagram_builder.go` |
| [`WriteRefactorOutputs`](go/internal/analysis/refactor_writer.go#L269) | function | `go/internal/analysis/refactor_writer.go` |
| [`DetectIssues`](go/internal/analysis/refactor_enricher.go#L99) | function | `go/internal/analysis/refactor_enricher.go` |
| [`ChunkFile`](go/internal/rag/chunker.go#L40) | function | `go/internal/rag/chunker.go` |
| [`VectorStore`](go/internal/rag/vector_store.go#L15) | type | `go/internal/rag/vector_store.go` |

> **Sources:** `go/cmd/rekipedia/main.go` · L6–L8 · [`main`](go/cmd/rekipedia/main.go#L6)  
> **Sources:** `go/cmd/rekipedia/cmd/root.go` · L44–L77 · [`Execute`](go/cmd/rekipedia/cmd/root.go#L44)  
> **Sources:** `go/cmd/rekipedia/cmd/ask.go` · L87–L174 · [`runInteractiveAsk`](go/cmd/rekipedia/cmd/ask.go#L87)  
> **Sources:** `go/cmd/rekipedia/cmd/refactor.go` · L57–L305 · [`Finding`](go/cmd/rekipedia/cmd/refactor.go#L57), [`staticWalk`](go/cmd/rekipedia/cmd/refactor.go#L75), [`buildStaticReport`](go/cmd/rekipedia/cmd/refactor.go#L148)  
> **Sources:** `go/internal/orchestrator/run_ask.go` · L59–L261 · [`RunAsk`](go/internal/orchestrator/run_ask.go#L59), [`buildContext`](go/internal/orchestrator/run_ask.go#L211)  
> **Sources:** `go/internal/storage/store.go` · L18–L335 · [`Store`](go/internal/storage/store.go#L18)  
> **Sources:** `go/internal/models/contracts.go` · L53–L156 · [`Symbol`](go/internal/models/contracts.go#L53), [`WikiPlan`](go/internal/models/contracts.go#L139)  

## Notes on What Is and Is Not Exposed

The Go command surface is mostly **package-private in implementation, public by convention in usage**:
- Most subcommand files use `init()` registration, which means their command objects are not listed as exported symbols in the analysis data.
- The real surface area is therefore best understood as the set of command files plus the exported orchestration and contract types they rely on.
- Several helper functions are unexported but still interface-relevant because they shape CLI behavior, such as [`loadLLMConfig`](go/cmd/rekipedia/cmd/scan.go#L143-L161), [`staticWalk`](go/cmd/rekipedia/cmd/refactor.go#L75-L127), and [`formatDiffMd`](go/cmd/rekipedia/cmd/diff.go#L175-L214).

The tests in `go/cmd/rekipedia/cmd/*.go` reinforce that these helpers are part of the stable command behavior, even when not exported. For example, the command registration tests in [`embed_export_update_test.go`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L17-L166) and [`refactor_test.go`](go/cmd/rekipedia/cmd/refactor_test.go#L15-L312) validate flags, `Use` lines, and command wiring.

> **Sources:** `go/cmd/rekipedia/cmd/embed_export_update_test.go` · L17–L166 · [`TestEmbedCmdRegistered`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L17), [`TestExportCmdRegistered`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L49), [`TestUpdateCmdRegistered`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L85)  
> **Sources:** `go/cmd/rekipedia/cmd/refactor_test.go` · L15–L312 · [`TestRefactorCmdRegistered`](go/cmd/rekipedia/cmd/refactor_test.go#L15), [`TestScanHasWithRefactorFlag`](go/cmd/rekipedia/cmd/refactor_test.go#L307)