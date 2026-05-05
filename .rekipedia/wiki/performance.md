---
slug: performance
title: "Performance Considerations in the Repository"
section: internals
tags: [internals, algorithms]
pin: false
importance: 50
created_at: 2026-05-05T04:25:44Z
rekipedia_version: 0.10.2
---

# Performance Considerations in the Repository

## Overview

This repository is structured around a scan → analyze → store → serve workflow, with several performance-sensitive paths that are clearly visible in the codebase. The most important considerations are:

1. **Repository-wide traversal and file processing** during snapshotting and static analysis.
2. **Graph-style analysis** over symbols and relationships, especially for fan-in/fan-out, cycles, and impact computations.
3. **LLM-backed enrichment and synthesis**, which is mostly I/O-bound but can still become expensive due to per-issue requests, prompt construction, and concurrency.
4. **Search and RAG flows**, where tokenization, ranking, chunking, and vector search can scale with corpus size.
5. **Database access and export paths**, which frequently materialize whole result sets and serialize them into JSON/Markdown/GraphML/ZIP.

There are no explicit benchmark artifacts in the provided analysis data, so this page focuses strictly on structural and code-level evidence rather than measured throughput.

> **Sources:** `go/internal/orchestrator/snapshotter.go` · `go/internal/analysis/refactor_detector.go` · `go/internal/analysis/refactor_enricher.go` · `go/internal/rag/chunker.go` · `go/internal/rag/vector_store.go` · `go/internal/storage/store.go`

## Hotspots

### 1) Repository scanning and snapshot generation

The snapshotting path starts in [`Snapshotter.Snapshot`](go/internal/orchestrator/snapshotter.go#L89) and uses helpers like [`sha256File`](go/internal/orchestrator/snapshotter.go#L149) and [`detectLanguage`](go/internal/orchestrator/snapshotter.go#L162). The shape of this code strongly suggests that snapshot cost grows with:

- the number of files under the repository root,
- the amount of file content that must be hashed,
- the number of paths filtered out or included.

Any SHA-256 computation is linear in file size, and filesystem traversal is naturally linear in the number of entries encountered. Because `Snapshotter` is used as the basis for later planning and digest/update flows, it is one of the most fundamental scaling points.

### 2) Static analysis over symbols and relationships

The refactor detector in [`DetectAll`](go/internal/analysis/refactor_detector.go#L404) aggregates several analyses: [`DetectGodNodes`](go/internal/analysis/refactor_detector.go#L30), [`DetectCircularDeps`](go/internal/analysis/refactor_detector.go#L103), [`DetectDeadCode`](go/internal/analysis/refactor_detector.go#L204), [`DetectHighFanIn`](go/internal/analysis/refactor_detector.go#L234), [`DetectHighFanOut`](go/internal/analysis/refactor_detector.go#L279), and [`DetectDeepInheritance`](go/internal/analysis/refactor_detector.go#L323). These routines repeatedly build lookup tables, iterate over symbols, and sort result sets.

The same pattern exists in graph-level helpers such as [`GetGodNodes`](go/internal/graph/graph_analysis.go#L21), [`GetHubNodes`](go/internal/graph/graph_analysis.go#L71), and [`GetKnowledgeGaps`](go/internal/graph/graph_analysis.go#L110). This is a classic hotspot class: repeated passes over the symbol/relationship graph, with sorts and set operations layered on top.

### 3) LLM enrichment

The enrichment path in [`RefactorEnricher.Enrich`](go/internal/analysis/refactor_enricher.go#L324) and [`(e *RefactorEnricher).EnrichAll`](go/internal/analysis/refactor_enricher.go#L308) can become expensive because it fan-outs to individual enrichment calls. The implementation uses concurrency, which helps wall-clock latency, but total work still scales with the number of issues being enriched. Prompt building in [`buildPrompt`](go/internal/analysis/refactor_enricher.go#L361) and response parsing in [`parseEnrichment`](go/internal/analysis/refactor_enricher.go#L407) are additional overheads.

### 4) Search and ranking

The CLI search path depends on [`tokenizeSymbol`](go/cmd/rekipedia/cmd/search.go#L20) and [`scoreBM25`](go/cmd/rekipedia/cmd/search.go#L54). The exposed structure implies that each query may tokenize multiple candidates and score them before sorting results. That is usually cheap for small datasets, but scales linearly with the number of indexed symbols or documents.

> **Sources:** `go/internal/orchestrator/snapshotter.go` · `go/internal/analysis/refactor_detector.go` · `go/internal/analysis/refactor_enricher.go` · `go/internal/graph/graph_analysis.go` · `go/cmd/rekipedia/cmd/search.go`

## Scaling Behavior

### Repository size scaling

Several core flows are fundamentally **O(n)** or **O(n log n)** in repository size, where `n` is the number of files, symbols, or relationships:

- [`Snapshotter.Snapshot`](go/internal/orchestrator/snapshotter.go#L89) scales with files walked and bytes hashed.
- [`ShardPlanner.Plan`](go/internal/orchestrator/sharding.go#L31) and [`(sp *ShardPlanner).splitGroup`](go/internal/orchestrator/sharding.go#L56) scale with the number of manifests and directory groups.
- [`ChunkFile`](go/internal/rag/chunker.go#L40) depends on content length and line count, with extra cost for chunk overlap and file-type-specific parsing.
- [`(v *VectorStore).Search`](go/internal/rag/vector_store.go#L71) scales with the number of stored vectors and the top-k selection strategy.
- [`ListSymbols`](go/internal/storage/store.go#L174) and [`ListRelationships`](go/internal/storage/store.go#L223) can grow with the total persisted dataset.

### Relationship-graph scaling

Several analyses use maps, sets, and sorting, which makes their scaling behavior sensitive to graph density:

- [`DetectCircularDeps`](go/internal/analysis/refactor_detector.go#L103) builds adjacency-like structures and traverses them for cycle discovery.
- [`DetectHighFanIn`](go/internal/analysis/refactor_detector.go#L234) and [`DetectHighFanOut`](go/internal/analysis/refactor_detector.go#L279) effectively depend on the degree distribution of the graph.
- [`compute_impact`](src/rekipedia/analysis/impact.py) uses BFS-like traversal structures (`deque`) and repeated set membership operations, so it scales with the reachable subgraph size rather than just the raw node count.

### Concurrency improves latency, not total work

Concurrency is used in:

- [`RunDigest`](go/internal/orchestrator/run_digest.go#L48) via `errgroup`,
- [`RefactorEnricher.Enrich`](go/internal/analysis/refactor_enricher.go#L324) via `ThreadPoolExecutor` in the Python implementation and concurrency in the Go implementation’s structure,
- [`search_all_repos`](src/rekipedia/analysis/cross_repo_search.py) via `ThreadPoolExecutor`.

This means the repository has some throughput-friendly design choices, but the total computational load still scales with input size. Concurrency is mainly a way to hide I/O latency or parallelize independent units of work.

> **Sources:** `go/internal/orchestrator/sharding.go` · `go/internal/rag/chunker.go` · `go/internal/rag/vector_store.go` · `go/internal/storage/store.go` · `go/internal/analysis/refactor_detector.go` · `src/rekipedia/analysis/impact.py` · `src/rekipedia/analysis/cross_repo_search.py`

## Caching, Batching, and Reuse

### Caching

The analysis data does not show a dedicated in-memory caching layer for analysis results or embeddings. However, there are a few persistence-based reuse mechanisms:

- [`WriteScanMeta`](go/internal/rag/scan_meta.go#L24) and [`ReadScanMeta`](go/internal/rag/scan_meta.go#L39) persist scan metadata, which avoids recomputing metadata manually.
- [`(v *VectorStore).Save`](go/internal/rag/vector_store.go#L96) and [`(v *VectorStore).Load`](go/internal/rag/vector_store.go#L108) serialize vector state for reuse.
- [`(s *Store).GetLatestRunID`](go/internal/storage/store.go#L134) and related `Store` methods allow the system to reuse the latest persisted run rather than rescan from scratch.
- [`loadWatchConfig`](go/cmd/rekipedia/cmd/watch.go#L18) and [`saveWatchConfig`](go/cmd/rekipedia/cmd/watch.go#L28) persist watch settings across runs.

These are not algorithmic caches in the strict sense, but they reduce repeated work across invocations.

### Batching

Batching is most visible in synthesis and orchestration:

- [`PageBuilder.BuildAll`](go/internal/synthesis/page_builder.go#L71) and [`(b *PageBuilder).BuildPage`](go/internal/synthesis/page_builder.go#L113) suggest page generation in groups, with [`buildPayload`](go/internal/synthesis/page_builder.go#L174) assembling structured input.
- [`RunDigest`](go/internal/orchestrator/run_digest.go#L48) aggregates shards and pages into a larger unit of work.
- [`ChunkFile`](go/internal/rag/chunker.go#L40) inherently batches source text into chunks for embedding/search.
- [`(e *EmbedPipeline).Build`](go/internal/rag/embedder.go#L30) is the most obvious batch-oriented pipeline: it walks files, chunks content, embeds in groups, and persists results.

The structural signal here is that expensive external work, especially embedding and LLM calls, is organized around batchable units rather than single-line or per-token calls.

### Deduplication and reuse of intermediate structures

Several helpers reduce repeated work or duplicate outputs:

- [`uniqueStrings`](go/internal/analysis/refactor_writer.go#L331)
- [`dedup`](go/internal/analysis/refactor_enricher.go#L506)
- [`uniqueFiles`](go/internal/analysis/refactor_enricher.go#L489)
- [`cycleKey`](go/internal/analysis/refactor_enricher.go#L466)

These are small but meaningful performance guards when result sets contain repeated findings or paths.

> **Sources:** `go/internal/rag/scan_meta.go` · `go/internal/rag/vector_store.go` · `go/internal/storage/store.go` · `go/cmd/rekipedia/cmd/watch.go` · `go/internal/synthesis/page_builder.go` · `go/internal/orchestrator/run_digest.go` · `go/internal/rag/embedder.go` · `go/internal/analysis/refactor_writer.go` · `go/internal/analysis/refactor_enricher.go`

## Likely Expensive Operations

| Operation | Relevant symbol(s) | Why it is expensive | Likely impact |
|---|---|---|---|
| File hashing during snapshotting | [`sha256File`](go/internal/orchestrator/snapshotter.go#L149), [`Snapshotter.Snapshot`](go/internal/orchestrator/snapshotter.go#L89) | Reads file contents and computes a digest for each tracked file | Linear in total file bytes; dominates on large repos |
| Full repository walk | [`Snapshotter.Snapshot`](go/internal/orchestrator/snapshotter.go#L89), [`fsutil.Walk`](go/pkg/fsutil/walk.go) | Traverses filesystem entries and applies filters | Linear in file count; can be costly on monorepos |
| Cycle detection | [`DetectCircularDeps`](go/internal/analysis/refactor_detector.go#L103), [`findCycles`](go/internal/analysis/refactor_enricher.go#L428) | Graph traversal plus deduplication and sorting | Sensitive to dense dependency graphs |
| Fan-in/fan-out analysis | [`DetectHighFanIn`](go/internal/analysis/refactor_detector.go#L234), [`DetectHighFanOut`](go/internal/analysis/refactor_detector.go#L279) | Builds counts over the whole relationship set | Linear in relationships; repeated lookups and sorting add overhead |
| Dead-code detection | [`DetectDeadCode`](go/internal/analysis/refactor_detector.go#L204) | Requires symbol lookups, filtering, and caller checks | Can be large when symbol tables are big |
| Embedding pipeline build | [`(e *EmbedPipeline).Build`](go/internal/rag/embedder.go#L30) | Chunking + LLM embedding + persistence | Often I/O-bound, but total work scales with corpus size |
| Vector similarity search | [`(v *VectorStore).Search`](go/internal/rag/vector_store.go#L71) | Search over stored vectors, then rank/sort results | Linear or near-linear in stored vectors depending on backend behavior |
| Page synthesis | [`(b *PageBuilder).BuildAll`](go/internal/synthesis/page_builder.go#L71) | Builds prompts/payloads across multiple pages | Expensive if many pages or large payloads are involved |
| Markdown / JSON export | [`(e *JSONExporter).Export`](go/internal/exporter/json_exporter.go#L49), [`(e *MarkdownExporter).Export`](go/internal/exporter/markdown_exporter.go#L22) | Materializes and serializes full result sets | Heavy on large datasets; CPU + I/O bound |
| Search ranking across symbols | [`tokenizeSymbol`](go/cmd/rekipedia/cmd/search.go#L20), [`scoreBM25`](go/cmd/rekipedia/cmd/search.go#L54) | Tokenization and per-document scoring for each query | Query latency grows with corpus size |

## Tests and Benchmark Evidence

### What the tests do show

The repository has strong **correctness-oriented tests** around the most performance-sensitive subsystems:

- [`TestFileTokenEstimate`](go/internal/orchestrator/orchestrator_test.go#L243) validates the token-estimation logic used for sharding.
- [`TestShardPlannerSplitsOnBudget`](go/internal/orchestrator/orchestrator_test.go#L157) exercises budget-based partitioning.
- [`TestSnapshotterSHA256Stable`](go/internal/orchestrator/orchestrator_test.go#L97) confirms deterministic hashing behavior.
- [`TestChunkFile_Overlap`](go/internal/rag/rag_test.go#L57) and related chunking tests verify chunk formation rules.
- [`TestVectorStore_SearchTopK`](go/internal/rag/rag_test.go#L100) checks top-k behavior.
- [`TestDetectCircularDeps_SimpleCycle`](go/internal/analysis/refactor_detector_test.go#L88), [`TestDetectHighFanIn_Detected`](go/internal/analysis/refactor_detector_test.go#L201), and [`TestDetectDeepInheritance_Detected`](go/internal/analysis/refactor_detector_test.go#L281) validate the graph analyzers.
- [`TestAttachCallersTop5`](go/internal/analysis/refactor_enricher_test.go#L198) checks that enrichment metadata is capped, which is a useful guard against payload growth.
- [`TestWriteRefactorOutputsCreatesFiles`](go/internal/analysis/refactor_writer_test.go#L287) and [`TestWriteRefactorOutputsSummaryCounts`](go/internal/analysis/refactor_writer_test.go#L342) verify output generation at a structural level.

### What is not present

No benchmark files or benchmark functions were included in the analysis payload. There is also no evidence of profiling output, latency targets, or runtime performance dashboards. So while the code structure strongly implies the hot paths listed above, there is no repository-provided benchmark data to quantify them.

> **Sources:** `go/internal/orchestrator/orchestrator_test.go` · `go/internal/rag/rag_test.go` · `go/internal/analysis/refactor_detector_test.go` · `go/internal/analysis/refactor_enricher_test.go` · `go/internal/analysis/refactor_writer_test.go`

## Practical Takeaways

### Where to optimize first

If performance becomes a problem, the most likely high-value targets are:

1. [`Snapshotter.Snapshot`](go/internal/orchestrator/snapshotter.go#L89) and [`sha256File`](go/internal/orchestrator/snapshotter.go#L149)
2. [`DetectAll`](go/internal/analysis/refactor_detector.go#L404) and the graph-oriented detectors it calls
3. [`(e *EmbedPipeline).Build`](go/internal/rag/embedder.go#L30)
4. [`RunDigest`](go/internal/orchestrator/run_digest.go#L48) and [`PageBuilder.BuildAll`](go/internal/synthesis/page_builder.go#L71)
5. [`(v *VectorStore).Search`](go/internal/rag/vector_store.go#L71) and [`tokenizeSymbol`](go/cmd/rekipedia/cmd/search.go#L20)

### General performance posture

The repository favors:
- **simple, linear scans** over complex indexing,
- **set/map-based deduplication** for correctness and modest efficiency,
- **concurrency** where operations are independent,
- **persistent outputs** to avoid recomputation across runs.

That is a sensible baseline for a tool that analyzes repositories and synthesizes documentation, but it also means the system’s runtime cost will track repository size fairly directly unless caching or incremental processing is expanded further.

> **Sources:** `go/internal/orchestrator/snapshotter.go` · `go/internal/analysis/refactor_detector.go` · `go/internal/rag/embedder.go` · `go/internal/orchestrator/run_digest.go` · `go/internal/synthesis/page_builder.go` · `go/internal/rag/vector_store.go` · `go/cmd/rekipedia/cmd/search.go`