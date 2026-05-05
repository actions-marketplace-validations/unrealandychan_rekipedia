---
slug: technical-debt
title: "Risk, TODO/FIXME, and Test Coverage Review"
section: development
tags: [development, contributing, internals]
pin: false
importance: 70
created_at: 2026-05-05T04:58:57Z
rekipedia_version: 0.10.3
---

# Risk, TODO/FIXME, and Test Coverage Review

## Issue Summary

This page focuses on maintenance risks, code smells, TODO/FIXME-like debt indicators, and test gaps observed in the repository. It is intentionally conservative: where the analysis data does **not** pre-flag a high-risk issue, that is called out explicitly rather than inferred.

| Category | Observed Risk Level | Evidence Themes | Primary Subsystems |
|---|---:|---|---|
| Debt detectors and remediation plumbing | Low–Moderate | Static refactor detectors exist, but no high-risk issues are pre-flagged in the provided evidence | [`go/cmd/rekipedia/cmd/refactor.go`](go/cmd/rekipedia/cmd/refactor.go), [`go/internal/analysis/refactor_detector.go`](go/internal/analysis/refactor_detector.go) |
| TODO/FIXME / explicit debt comments | Low visibility | Static data does not include comment extraction, so only indirect debt logic is observable | Refactor, analysis, orchestration |
| Test gaps in command-line flows | Moderate | Strong command registration tests, but limited evidence of end-to-end failure-path coverage across every command | [`go/cmd/rekipedia/cmd/*.go`](go/cmd/rekipedia/cmd/root.go), [`go/cmd/rekipedia/cmd/refactor_test.go`](go/cmd/rekipedia/cmd/refactor_test.go) |
| Test gaps in server edge cases | Moderate | Many route tests exist, but sparse evidence of adversarial inputs, concurrency, and storage failure simulations | [`go/internal/server/server.go`](go/internal/server/server.go), [`go/internal/server/server_test.go`](go/internal/server/server_test.go) |
| Risky implementation patterns | Moderate | Several modules rely on heuristics, string parsing, and filesystem walking; these are manageable but maintenance-sensitive | analysis, extractor, orchestrator, server |
| Cross-module maintenance coupling | Moderate | Orchestrator, storage, synthesis, and server are tightly connected via shared contracts | [`go/internal/models/contracts.go`](go/internal/models/contracts.go), [`go/internal/orchestrator/run_digest.go`](go/internal/orchestrator/run_digest.go) |

> **Sources:** `go/cmd/rekipedia/cmd/refactor.go` · L57–L175 · [`Finding`](go/cmd/rekipedia/cmd/refactor.go#L57) · [`staticWalk`](go/cmd/rekipedia/cmd/refactor.go#L75) · [`applyFilter`](go/cmd/rekipedia/cmd/refactor.go#L130) · [`buildStaticReport`](go/cmd/rekipedia/cmd/refactor.go#L148); `go/internal/analysis/refactor_detector.go` · L19–L413 · [`DetectDeadCode`](go/internal/analysis/refactor_detector.go#L204)

## Debt Signals and Refactor Detection

The repository does contain explicit debt-oriented logic, but it is framed as tooling rather than as a pre-existing “red alert” result set. In particular, [`staticWalk`](go/cmd/rekipedia/cmd/refactor.go#L75) scans the repository for TODO/FIXME-style findings, while [`applyFilter`](go/cmd/rekipedia/cmd/refactor.go#L130) narrows the report by severity before [`buildStaticReport`](go/cmd/rekipedia/cmd/refactor.go#L148) formats the output. That pipeline is complemented by programmatic detectors in [`DetectDeadCode`](go/internal/analysis/refactor_detector.go#L204), [`DetectCircularDeps`](go/internal/analysis/refactor_detector.go#L103), [`DetectHighFanIn`](go/internal/analysis/refactor_detector.go#L234), [`DetectHighFanOut`](go/internal/analysis/refactor_detector.go#L279), and [`DetectDeepInheritance`](go/internal/analysis/refactor_detector.go#L323).

The important maintenance takeaway is that the repository has already invested in “debt visibility” primitives. However, the static evidence supplied here does **not** include a precomputed list of high-risk findings from these detectors. So, from an audit perspective, the safest statement is:

- the codebase has **debt detection capabilities**,
- tests exist for those detectors,
- but **no high-risk issues were pre-flagged in the supplied analysis data**.

That matters because it prevents overinterpreting the presence of detectors as proof that the repository currently contains severe structural debt.

### What the detectors cover

The detector suite in [`go/internal/analysis/refactor_detector.go`](go/internal/analysis/refactor_detector.go) focuses on structural smells rather than business logic bugs:

- [`DetectDeadCode`](go/internal/analysis/refactor_detector.go#L204) flags likely unused private symbols.
- [`DetectCircularDeps`](go/internal/analysis/refactor_detector.go#L103) looks for module cycles.
- [`DetectHighFanIn`](go/internal/analysis/refactor_detector.go#L234) and [`DetectHighFanOut`](go/internal/analysis/refactor_detector.go#L279) measure coupling pressure.
- [`DetectDeepInheritance`](go/internal/analysis/refactor_detector.go#L323) surfaces inheritance chains.

These are good maintenance sentinels, but they also reveal a potential risk pattern: the codebase depends on heuristics and convention-based filtering. That is acceptable for a static analysis tool, but it means the output should be treated as advisory unless backed by tests or manual review.

> **Sources:** `go/cmd/rekipedia/cmd/refactor.go` · L75–L175 · [`staticWalk`](go/cmd/rekipedia/cmd/refactor.go#L75) · [`applyFilter`](go/cmd/rekipedia/cmd/refactor.go#L130); `go/internal/analysis/refactor_detector.go` · L103–L413 · [`DetectCircularDeps`](go/internal/analysis/refactor_detector.go#L103) · [`DetectDeadCode`](go/internal/analysis/refactor_detector.go#L204) · [`DetectHighFanIn`](go/internal/analysis/refactor_detector.go#L234) · [`DetectHighFanOut`](go/internal/analysis/refactor_detector.go#L279) · [`DetectDeepInheritance`](go/internal/analysis/refactor_detector.go#L323)

## Subsystem Risk Review

### CLI and command wiring

The CLI layer is relatively well covered by registration and flag tests, especially around command presence and option plumbing such as [`TestRefactorCmdRegistered`](go/cmd/rekipedia/cmd/refactor_test.go#L15), [`TestRefactorCmdFlags`](go/cmd/rekipedia/cmd/refactor_test.go#L28), and [`TestRootCommandHasSubcommands`](go/cmd/rekipedia/cmd/root_test.go#L19). That is a good baseline.

The maintenance risk is not “missing tests entirely,” but rather that most tests validate command shape rather than robust behavioral failure modes. For example, the refactor command has targeted tests for [`staticWalk`](go/cmd/rekipedia/cmd/refactor_test.go#L65) and [`applyFilter`](go/cmd/rekipedia/cmd/refactor_test.go#L156), but the evidence does not show broad coverage for malformed repository layouts, partial filesystem failures, or large-repo performance boundaries. Similarly, commands like [`ask_cmd`](src/rekipedia/cli/ask.py) and [`export_cmd`](src/rekipedia/cli/export.py) are heavily interactive and file-system oriented, which typically increases the need for negative-path tests.

**Maintenance concern:** command orchestration logic is doing a lot of filesystem and UX work inline. That raises the cost of change, because output formatting, I/O, and control flow are coupled in the same command definitions.

> **Sources:** `go/cmd/rekipedia/cmd/refactor_test.go` · L15–L312 · [`TestStaticWalkFindsTODO`](go/cmd/rekipedia/cmd/refactor_test.go#L65) · [`TestApplyFilterAll`](go/cmd/rekipedia/cmd/refactor_test.go#L156); `go/cmd/rekipedia/cmd/root_test.go` · L9–L110 · [`TestRootCommandHasSubcommands`](go/cmd/rekipedia/cmd/root_test.go#L19)

### Analysis and refactor subsystem

This is the subsystem with the clearest evidence of deliberate debt-handling. The detector code is exercised by a broad test matrix, including [`TestDetectDeadCode_GoUnexportedFlagged`](go/internal/analysis/refactor_detector_test.go#L164), [`TestDetectCircularDeps_SimpleCycle`](go/internal/analysis/refactor_detector_test.go#L88), [`TestDetectHighFanOut_Detected`](go/internal/analysis/refactor_detector_test.go#L241), and [`TestDetectDeepInheritance_Detected`](go/internal/analysis/refactor_detector_test.go#L281).

The main risk here is not missing correctness tests, but the fact that these detectors rely on conventions:

- exported-vs-unexported naming via [`isExported`](go/internal/analysis/refactor_detector.go#L19),
- caller/callee relationships derived from symbol metadata,
- and repository-specific filtering behavior in [`DetectDeadCode`](go/internal/analysis/refactor_detector.go#L204).

This makes the subsystem sensitive to unusual language idioms or incomplete metadata. The test suite mitigates that risk well, but users should still treat detector output as a triage aid, not as a final authority.

> **Sources:** `go/internal/analysis/refactor_detector.go` · L19–L413 · [`isExported`](go/internal/analysis/refactor_detector.go#L19) · [`DetectDeadCode`](go/internal/analysis/refactor_detector.go#L204); `go/internal/analysis/refactor_detector_test.go` · L16–L394

### Orchestrator and synthesis pipeline

The orchestrator layer combines snapshotting, sharding, LLM usage, and storage access across [`RunDigest`](go/internal/orchestrator/run_digest.go#L48), [`RunUpdate`](go/internal/orchestrator/run_update.go#L30), and [`RunAsk`](go/internal/orchestrator/run_ask.go#L59). That breadth is the main maintenance risk: multiple responsibilities converge here, and failure modes can be cross-cutting.

The tests are reasonably extensive for happy paths and deterministic helper behavior, especially around sharding and snapshotting in [`TestShardPlannerSplitsOnBudget`](go/internal/orchestrator/orchestrator_test.go#L157), [`TestSnapshotterSHA256Stable`](go/internal/orchestrator/orchestrator_test.go#L97), and [`TestSnapshotterLanguageDetection`](go/internal/orchestrator/orchestrator_test.go#L68). But the static evidence does not show much around:

- LLM partial failures,
- storage outages during orchestration,
- or concurrent race-style conditions when coordinating multiple shards.

**Pattern risk:** orchestration code often becomes “glue code that never leaves the critical path.” That can age poorly unless error handling and retries remain tightly tested.

> **Sources:** `go/internal/orchestrator/run_ask.go` · L59–L261 · [`RunAsk`](go/internal/orchestrator/run_ask.go#L59) · [`buildContext`](go/internal/orchestrator/run_ask.go#L211); `go/internal/orchestrator/run_digest.go` · L48–L396 · [`RunDigest`](go/internal/orchestrator/run_digest.go#L48); `go/internal/orchestrator/run_update.go` · L30–L179 · [`RunUpdate`](go/internal/orchestrator/run_update.go#L30); `go/internal/orchestrator/orchestrator_test.go` · L13–L302

### Server and storage

The server surface is well exercised at the route level: [`TestHealth`](go/internal/server/server_test.go#L27), [`TestAPIPages`](go/internal/server/server_test.go#L42), [`TestAPIPageFound`](go/internal/server/server_test.go#L72), [`TestAPIGraph`](go/internal/server/server_test.go#L203), and [`TestAPIAskBadJSON`](go/internal/server/server_test.go#L187) show that common endpoints and basic error responses are covered.

The risk is more subtle: the server code is large and deeply integrated with storage, templating, graph generation, and ask-streaming in [`go/internal/server/server.go`](go/internal/server/server.go). That makes regressions likely when data contracts evolve. The storage layer itself is also a maintenance hotspot because it owns schema migrations in [`migrate`](go/internal/storage/store.go#L48), run lifecycle management in [`CreateRun`](go/internal/storage/store.go#L116) / [`FinishRun`](go/internal/storage/store.go#L125), and query APIs such as [`ListWikiPages`](go/internal/storage/store.go#L270) and [`ListRelationships`](go/internal/storage/store.go#L223).

The tests are good, but the evidence does not clearly show fault injection around database corruption, transaction rollback failures, or concurrent write contention. Those are the types of issues that tend to surface in long-lived storage-backed services.

> **Sources:** `go/internal/server/server.go` · L35–L955 · [`handleAPIAsk`](go/internal/server/server.go#L274) · [`handleAPIGraph`](go/internal/server/server.go#L649) · [`gatherStats`](go/internal/server/server.go#L414); `go/internal/server/server_test.go` · L27–L396; `go/internal/storage/store.go` · L24–L335 · [`migrate`](go/internal/storage/store.go#L48) · [`ListRelationships`](go/internal/storage/store.go#L223)

## Test Coverage Gaps by Subsystem

| Subsystem | What is well covered | What appears sparse or absent |
|---|---|---|
| Refactor analysis | Detector correctness and edge cases, including cycles and dead code | Performance/scale scenarios, mixed-language metadata ambiguity |
| CLI commands | Command registration, flags, and some output generation | Comprehensive failure-path coverage and malformed input handling |
| Orchestrator | Planning, sharding, snapshot utilities, fallback paths | Storage/LLM outage injection, race/concurrency scenarios |
| Server | Route presence, rendering, JSON errors, and basic store-backed queries | Adversarial inputs, load/concurrency, persistence failure cases |
| Storage | Lifecycle, CRUD, alias methods, and missing-row behavior | Migration rollback/failure semantics, concurrent access pressure |
| RAG/extractors | Language-specific extraction and chunking behavior | Very large repositories, malformed source files beyond the basic fixtures |

The strongest pattern in the test suite is that most core happy paths are covered. The weaker area is *resilience testing*: simulating broken dependencies, malformed inputs at scale, and transient infrastructure failures.

This does not imply the repository is unsafe; it means the highest maintenance value likely lies in increasing failure-path and integration coverage, especially around the orchestration and persistence edges.

> **Sources:** `go/internal/analysis/refactor_detector_test.go` · L16–L394; `go/internal/orchestrator/orchestrator_test.go` · L13–L302; `go/internal/server/server_test.go` · L27–L396; `go/internal/storage/store_test.go` · L22–L389; `go/internal/rag/rag_test.go` · L12–L297; `go/internal/extractor/extractor_test.go` · L49–L516

## Maintenance Concerns Worth Watching

### Heuristic-heavy logic

Several modules use heuristic parsing or text-driven classification rather than structured semantic models. Examples include [`tokenizeSymbol`](go/cmd/rekipedia/cmd/search.go#L20), [`scoreBM25`](go/cmd/rekipedia/cmd/search.go#L54), [`detectLanguage`](go/internal/orchestrator/snapshotter.go#L162), [`peekDocstring`](go/internal/extractor/python.go#L153), and [`lineOf`](go/internal/extractor/typescript.go#L144). These are all reasonable implementation choices, but they deserve regression tests whenever supported languages or repository shapes expand.

### Tightly coupled shared contracts

Core types in [`go/internal/models/contracts.go`](go/internal/models/contracts.go) — such as [`LLMConfig`](go/internal/models/contracts.go#L6), [`AnalysisResult`](go/internal/models/contracts.go#L82), [`WikiPlan`](go/internal/models/contracts.go#L139), and [`ScanMeta`](go/internal/models/contracts.go#L147) — are used across orchestrator, storage, server, and synthesis. Shared contracts lower duplication but increase blast radius when changed.

### Output-format sensitivity

Markdown and JSON exporters, the server’s template rendering, and CLI output all depend on consistent field shapes and stable ordering. That is usually where “small” changes turn into broad regressions. The existing tests around [`BuildMarkdown`](go/internal/analysis/refactor_writer.go#L177), [`WriteRefactorOutputs`](go/internal/analysis/refactor_writer.go#L269), [`JSONExporter.Export`](go/internal/exporter/json_exporter.go#L49), and server template rendering are valuable because they pin this behavior down.

## Bottom Line

The supplied static evidence does **not** show pre-flagged high-risk debt. Instead, it shows a mature codebase with explicit debt-detection tooling, a good baseline of unit and route tests, and a few predictable maintenance hotspots:

- heuristic-heavy analysis and parsing,
- cross-module contract coupling,
- orchestration glue that spans multiple concerns,
- and weaker evidence of failure-injection tests than of happy-path tests.

That is a manageable risk profile, but one that benefits from continued investment in resilience testing and clear contract boundaries.

> **Sources:** `go/cmd/rekipedia/cmd/refactor.go` · L57–L175 · [`staticWalk`](go/cmd/rekipedia/cmd/refactor.go#L75) · [`applyFilter`](go/cmd/rekipedia/cmd/refactor.go#L130); `go/internal/analysis/refactor_detector.go` · L204–L413 · [`DetectDeadCode`](go/internal/analysis/refactor_detector.go#L204); `go/internal/models/contracts.go` · L6–L156