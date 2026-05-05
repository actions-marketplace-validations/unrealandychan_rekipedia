---
slug: technical-debt
title: "Debt Analysis: TODOs, Code Smells, Test Gaps, and Dependency Risks"
section: development
tags: [development, internals, contributing]
pin: false
importance: 50
created_at: 2026-05-05T04:25:57Z
rekipedia_version: 0.10.2
---

# Debt Analysis: TODOs, Code Smells, Test Gaps, and Dependency Risks

## Executive Summary

The repository contains a purpose-built static analysis path for debt discovery, and the strongest evidence shows that debt is concentrated in the Go command/analysis layer rather than the Python CLI wrappers. The key debt-reporting pipeline is implemented in [`staticWalk`](go/cmd/rekipedia/cmd/refactor.go#L75), [`applyFilter`](go/cmd/rekipedia/cmd/refactor.go#L130), [`buildStaticReport`](go/cmd/rekipedia/cmd/refactor.go#L148), and sorted by [`severityIndex`](go/cmd/rekipedia/cmd/refactor.go#L65). Those functions are directly exercised by tests such as [`TestStaticWalkFindsTODO`](go/cmd/rekipedia/cmd/refactor_test.go#L65), [`TestStaticWalkFindsFIXME`](go/cmd/rekipedia/cmd/refactor_test.go#L87), and the filter/report tests in [`go/cmd/rekipedia/cmd/refactor_test.go`](go/cmd/rekipedia/cmd/refactor_test.go#L156).

What is observable from the codebase is that debt reporting is intentionally centralized around TODO/FIXME scanning and a few structural smells (god nodes, circular deps, dead code, high fan-in/out, deep inheritance) via [`DetectAll`](go/internal/analysis/refactor_detector.go#L404). The debt surface is therefore not random: it is concentrated in the refactor command and the analysis package beneath it, with the CLI plumbing mostly acting as a thin frontend. The largest maintenance risk is that the same modules responsible for finding debt also contain broad import surfaces and operational complexity, especially the orchestration path in [`RunDigest`](go/internal/orchestrator/run_digest.go#L48), [`RunUpdate`](go/internal/orchestrator/run_update.go#L30), and the storage-backed command handlers in [`go/cmd/rekipedia/cmd/*.go`](go/cmd/rekipedia/cmd/refactor.go).

The table below summarizes the main findings and points to concrete next steps grounded in the repository evidence.

## Findings Summary

| Area | Evidence | Risk | Suggested Follow-up |
|------|----------|------|---------------------|
| Code Smells | TODO/FIXME scanning in [`staticWalk`](go/cmd/rekipedia/cmd/refactor.go#L75) and debt classification in [`severityIndex`](go/cmd/rekipedia/cmd/refactor.go#L65); structural smell detectors in [`DetectGodNodes`](go/internal/analysis/refactor_detector.go#L30), [`DetectCircularDeps`](go/internal/analysis/refactor_detector.go#L103), [`DetectDeadCode`](go/internal/analysis/refactor_detector.go#L204), [`DetectHighFanIn`](go/internal/analysis/refactor_detector.go#L234), [`DetectHighFanOut`](go/internal/analysis/refactor_detector.go#L279), and [`DetectDeepInheritance`](go/internal/analysis/refactor_detector.go#L323) | Smells are already present and codified; they can accumulate unless surfaced consistently in reports | Prioritize the exact files returned by `staticWalk`, then review the highest-severity issues from `buildStaticReport` and `DetectAll` |
| Test Gaps | Tests exist for scanner behavior in [`refactor_test.go`](go/cmd/rekipedia/cmd/refactor_test.go#L65), but there is no evidence of tests covering false positives/negatives for TODO/FIXME detection across all supported file types; several operational paths in `RunDigest`/`RunUpdate` are only indirectly covered | Debt detector can miss or over-report issues, especially outside currently exercised fixture patterns | Add targeted tests for mixed-comment formats, edge cases in `applyFilter`, and report ordering stability in `buildStaticReport` |
| Dependency Risks | `go/internal/llm/client.go` imports `github.com/sashabaranov/go-openai`, `go/internal/rag/vector_store.go` imports `github.com/philippgille/chromem-go`, `go/internal/storage/store.go` imports `modernc.org/sqlite`, and `go/internal/server/server.go` imports `github.com/go-chi/chi/v5` and `github.com/yuin/goldmark` | External package changes or runtime incompatibilities could affect core workflows, especially LLM, storage, and server features | Track the runtime-critical packages first; verify lockfile and CI coverage around LLM, vector store, and SQLite-backed storage |
| Maintenance Hotspots | Broad, multi-import command modules such as [`go/cmd/rekipedia/cmd/refactor.go`](go/cmd/rekipedia/cmd/refactor.go), [`go/internal/orchestrator/run_digest.go`](go/internal/orchestrator/run_digest.go#L48), and [`go/internal/server/server.go`](go/internal/server/server.go#L71) | High change surface increases the chance of regressions and debt drift | Focus review effort on these modules whenever debt reports mention them; they sit on top of many call chains |

> **Sources:** `go/cmd/rekipedia/cmd/refactor.go` · L65–L175 · [`severityIndex`](go/cmd/rekipedia/cmd/refactor.go#L65), [`staticWalk`](go/cmd/rekipedia/cmd/refactor.go#L75), [`applyFilter`](go/cmd/rekipedia/cmd/refactor.go#L130), [`buildStaticReport`](go/cmd/rekipedia/cmd/refactor.go#L148) · `go/internal/analysis/refactor_detector.go` · L30–L413 · [`DetectAll`](go/internal/analysis/refactor_detector.go#L404)

## Code Smells

The repository’s static-analysis model is explicit about the kinds of smells it can detect. In [`go/internal/analysis/refactor_detector.go`](go/internal/analysis/refactor_detector.go), smell detection is split into focused functions: [`DetectGodNodes`](go/internal/analysis/refactor_detector.go#L30), [`DetectCircularDeps`](go/internal/analysis/refactor_detector.go#L103), [`DetectDeadCode`](go/internal/analysis/refactor_detector.go#L204), [`DetectHighFanIn`](go/internal/analysis/refactor_detector.go#L234), [`DetectHighFanOut`](go/internal/analysis/refactor_detector.go#L279), and [`DetectDeepInheritance`](go/internal/analysis/refactor_detector.go#L323). This is important because it tells us where the repository itself believes debt lives: large hub-like nodes, dependency cycles, unused code, and highly connected modules.

The command-layer scanner is a separate but complementary source of code-debt evidence. [`staticWalk`](go/cmd/rekipedia/cmd/refactor.go#L75) traverses the repository and emits findings for TODO and FIXME-style comments; the tests prove the scanner explicitly recognizes TODOs, FIXMEs, and skips `.git` and `node_modules` trees via [`TestStaticWalkFindsTODO`](go/cmd/rekipedia/cmd/refactor_test.go#L65), [`TestStaticWalkFindsFIXME`](go/cmd/rekipedia/cmd/refactor_test.go#L87), [`TestStaticWalkSkipsGitDir`](go/cmd/rekipedia/cmd/refactor_test.go#L106), and [`TestStaticWalkSkipsNodeModules`](go/cmd/rekipedia/cmd/refactor_test.go#L125). That implies the code-smell surface is not just architectural; it also includes comment-based debt and possibly any adjacent “manual follow-up” markers that the regexes in `refactor.go` are configured to detect.

A notable maintenance pattern is that the modules used for analysis are themselves fairly broad. For example, [`go/internal/analysis/refactor_enricher.go`](go/internal/analysis/refactor_enricher.go) imports concurrency primitives and an LLM client, while [`go/internal/analysis/refactor_writer.go`](go/internal/analysis/refactor_writer.go) is responsible both for issue detection and markdown output. That’s not automatically a bug, but it means changes to formatting, ranking, or prompt generation can affect reporting quality in ways that are hard to isolate.

### Where smells are most concentrated

The strongest concentration is in the Go analysis/command surface:

- [`go/cmd/rekipedia/cmd/refactor.go`](go/cmd/rekipedia/cmd/refactor.go) — scanner, filter, report builder, and CLI registration.
- [`go/internal/analysis/refactor_detector.go`](go/internal/analysis/refactor_detector.go) — structural smell detectors.
- [`go/internal/analysis/refactor_enricher.go`](go/internal/analysis/refactor_enricher.go) — enrichment logic and cycle/caller attachment.
- [`go/internal/analysis/refactor_writer.go`](go/internal/analysis/refactor_writer.go) — issue classification and markdown/JSON writing.

These are the most likely places where debt is both detected and materialized into outputs.

> **Sources:** `go/cmd/rekipedia/cmd/refactor.go` · L57–L305 · [`severityIndex`](go/cmd/rekipedia/cmd/refactor.go#L65), [`staticWalk`](go/cmd/rekipedia/cmd/refactor.go#L75), [`applyFilter`](go/cmd/rekipedia/cmd/refactor.go#L130), [`buildStaticReport`](go/cmd/rekipedia/cmd/refactor.go#L148) · `go/internal/analysis/refactor_detector.go` · L30–L413 · [`DetectGodNodes`](go/internal/analysis/refactor_detector.go#L30), [`DetectCircularDeps`](go/internal/analysis/refactor_detector.go#L103), [`DetectDeadCode`](go/internal/analysis/refactor_detector.go#L204), [`DetectHighFanIn`](go/internal/analysis/refactor_detector.go#L234), [`DetectHighFanOut`](go/internal/analysis/refactor_detector.go#L279), [`DetectDeepInheritance`](go/internal/analysis/refactor_detector.go#L323)

## Test Gaps

The repository does contain direct tests for the refactor scanner and reporter, but the evidence suggests the coverage is narrower than the debt surface. In [`go/cmd/rekipedia/cmd/refactor_test.go`](go/cmd/rekipedia/cmd/refactor_test.go), the tests verify the happy path and a few key behaviors: TODO detection, FIXME detection, directory skipping, filter levels, and empty report handling. The report builder is also exercised through [`TestBuildStaticReportEmpty`](go/cmd/rekipedia/cmd/refactor_test.go#L207) and [`TestBuildStaticReportWithFindings`](go/cmd/rekipedia/cmd/refactor_test.go#L217).

What is not evidenced is broader negative testing around the debt scanner itself. For example, there is no direct evidence of tests covering:

- false positives in comment parsing across different file syntaxes,
- multiple TODO/FIXME markers in a single file,
- ordering stability across mixed-severity findings,
- empty/whitespace-only files,
- interaction between `applyFilter` and report rendering when findings are filtered down to zero,
- or multi-file debt concentration behavior, where one file contains several TODOs and another contains one critical issue.

The static-analysis side is also only partially tested by proxy. [`DetectAll`](go/internal/analysis/refactor_detector.go#L404) aggregates the detector suite, but the tests shown are primarily unit-level, not end-to-end against a real repository snapshot. The same is true of the enrichment and writer layers: there are tests for individual functions, but no evidence of a full scan pipeline assertion that starts from `staticWalk` and ends with a persisted report through [`buildStaticReport`](go/cmd/rekipedia/cmd/refactor.go#L148).

A practical takeaway is that the repository is strongest when the debt format is predictable and the inputs are synthetic. The biggest test gap is confidence in the scanner/reporting pipeline on real, mixed repository content — which matters because the page you asked for is specifically about TODO/FIXME and smell discovery.

> **Sources:** `go/cmd/rekipedia/cmd/refactor_test.go` · L65–L312 · [`TestStaticWalkFindsTODO`](go/cmd/rekipedia/cmd/refactor_test.go#L65), [`TestStaticWalkFindsFIXME`](go/cmd/rekipedia/cmd/refactor_test.go#L87), [`TestApplyFilterAll`](go/cmd/rekipedia/cmd/refactor_test.go#L156), [`TestBuildStaticReportWithFindings`](go/cmd/rekipedia/cmd/refactor_test.go#L217)

## Dependency Risks

The dependency risk profile is concentrated in a few core runtime packages that sit beneath important user-facing flows.

The LLM client in [`go/internal/llm/client.go`](go/internal/llm/client.go) depends on [`github.com/sashabaranov/go-openai`](go/internal/llm/client.go). That dependency is central because it is used by the ask/digest/update paths via [`RunAsk`](go/internal/orchestrator/run_ask.go#L59), [`RunDigest`](go/internal/orchestrator/run_digest.go#L48), and synthesis/prompting code such as [`NewPlannerAgent`](go/internal/synthesis/planner.go#L82). If this package changes behavior, it affects several user-visible commands at once.

The storage layer depends on [`modernc.org/sqlite`](go/internal/storage/store.go#L24) through [`go/internal/storage/store.go`](go/internal/storage/store.go), and the repository also uses [`github.com/philippgille/chromem-go`](go/internal/rag/vector_store.go#L27) in the vector store. Those are not interchangeable dependencies because they back persistent state and search data. Any incompatibility or regression there would cascade into reporting, history, and RAG search behavior.

On the server side, [`go/internal/server/server.go`](go/internal/server/server.go) imports [`github.com/go-chi/chi/v5`](go/internal/server/server.go#L50) and [`github.com/yuin/goldmark`](go/internal/server/server.go#L50). The server also bridges to storage and orchestrator code, so operational risk is not limited to the web layer; it spans the full wiki presentation stack.

The Go command modules are also imported by the main CLI entry points. That means dependency failure in one lower layer can surface in several commands without much insulation. The strongest observable risk is not an abstract “vendor lock-in” issue; it is that the repository’s core workflows are coupled to a small set of external packages that sit on hot paths.

> **Sources:** `go/internal/llm/client.go` · L110–L385 · [`Client`](go/internal/llm/client.go#L110), [`CallWithRetry`](go/internal/llm/client.go#L166), [`Embed`](go/internal/llm/client.go#L234) · `go/internal/storage/store.go` · L18–L335 · [`Store`](go/internal/storage/store.go#L18), [`Open`](go/internal/storage/store.go#L24), [`migrate`](go/internal/storage/store.go#L48) · `go/internal/rag/vector_store.go` · L15–L118 · [`VectorStore`](go/internal/rag/vector_store.go#L15), [`Search`](go/internal/rag/vector_store.go#L71)

## Maintenance Hotspots

The highest-maintenance areas are the ones that both orchestrate behavior and aggregate many imports. In practice, that means the refactor command, the digest/update orchestration, and the server.

`go/cmd/rekipedia/cmd/refactor.go` is a clear hotspot because it combines filesystem walking, comment scanning, severity ranking, filtering, and report assembly through [`staticWalk`](go/cmd/rekipedia/cmd/refactor.go#L75), [`applyFilter`](go/cmd/rekipedia/cmd/refactor.go#L130), and [`buildStaticReport`](go/cmd/rekipedia/cmd/refactor.go#L148). Whenever debt output changes, this file is likely involved.

`go/internal/orchestrator/run_digest.go` is another hotspot. It imports the analysis, extractor, LLM, storage, and synthesis layers, and [`RunDigest`](go/internal/orchestrator/run_digest.go#L48) coordinates them. This is a classic fan-out point: changes there can influence sharding, progress reporting, enrichment, and persistence simultaneously.

The web server in [`go/internal/server/server.go`](go/internal/server/server.go) is also a maintenance focal point because it composes routing, rendering, API handlers, wiki page lookup, graph generation, and QA persistence. It has many sub-handlers, including [`handleAPIAsk`](go/internal/server/server.go#L274), [`handleAPIHistory`](go/internal/server/server.go#L300), [`handleAPIGraph`](go/internal/server/server.go#L649), and [`handleAPIWikiSearch`](go/internal/server/server.go#L802). That makes it a likely location for regression-prone changes whenever the storage schema or wiki format shifts.

### Concentration signal from the analyzer

Because the repository’s own analyzer surfaces issues through [`DetectAll`](go/internal/analysis/refactor_detector.go#L404) and the command layer ranks them with [`severityIndex`](go/cmd/rekipedia/cmd/refactor.go#L65), the most debt-concentrated zones are the same modules that already have the broadest responsibilities. The codebase is, in effect, telling us where to look:

1. the refactor command/reporting path,
2. the orchestration pipeline,
3. the server/storage boundary,
4. and the LLM/vector-store integrations.

Those are the places where TODO/FIXME comments and structural smells are most likely to remain visible and operationally relevant.

> **Sources:** `go/internal/orchestrator/run_digest.go` · L48–L396 · [`RunDigest`](go/internal/orchestrator/run_digest.go#L48), [`extractShard`](go/internal/orchestrator/run_digest.go#L313), [`combineResults`](go/internal/orchestrator/run_digest.go#L346) · `go/internal/server/server.go` · L71–L926 · [`Start`](go/internal/server/server.go#L71), [`handleAPIAsk`](go/internal/server/server.go#L274), [`handleAPIGraph`](go/internal/server/server.go#L649), [`handleAPIWikiSearch`](go/internal/server/server.go#L802)