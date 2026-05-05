---
slug: python-api
title: "Public Python-Facing API Reference"
section: api-reference
tags: [api, reference]
pin: false
importance: 64
created_at: 2026-05-05T04:59:13Z
rekipedia_version: 0.10.3
---

# Public Python-Facing API Reference

## Overview

This page documents the public implementation symbols that are part of the repository’s runtime/library surface, with emphasis on callable shapes and data types rather than architecture or setup. The most visible Python-facing API lives in the Go extractor package, where [`PythonExtractor`](go/internal/extractor/python.go#L25) exposes extraction behavior and [`ExtractPythonFromReader`](go/internal/extractor/python.go#L188) provides a reader-oriented entry point. The core runtime also includes shared contracts such as [`Symbol`](go/internal/models/contracts.go#L53), [`Relationship`](go/internal/models/contracts.go#L64), and [`AnalysisResult`](go/internal/models/contracts.go#L82), plus orchestration and storage primitives that are used across the library surface.

Although this repository is primarily Go-based, the public-facing runtime model is still organized around language extraction, analysis, storage, synthesis, and serving. For Python-specific consumers, the most relevant surface is the extractor implementation and the shared model types it populates.

> **Sources:** `go/internal/extractor/python.go` · L25–L201 · [`PythonExtractor`](go/internal/extractor/python.go#L25) · [`ExtractPythonFromReader`](go/internal/extractor/python.go#L188)

## Python Extraction API

The Python extractor is responsible for handling Python source files and converting them into repository symbols and relationships. The concrete implementation is [`PythonExtractor`](go/internal/extractor/python.go#L25), created via [`NewPythonExtractor`](go/internal/extractor/python.go#L28). It implements the standard extractor contract through [`(e *PythonExtractor).CanHandle`](go/internal/extractor/python.go#L31) and [`(e *PythonExtractor).Extract`](go/internal/extractor/python.go#L37).

A notable convenience API is [`ExtractPythonFromReader`](go/internal/extractor/python.go#L188), which supports extracting from an `io.Reader` rather than a file path. This is especially useful for tooling, tests, and in-memory integration points.

### Functions

| Function | Signature / Shape | Description |
|---|---|---|
| [`NewPythonExtractor`](go/internal/extractor/python.go#L28) | constructor | Creates a new [`PythonExtractor`](go/internal/extractor/python.go#L25). |
| [`(e *PythonExtractor).CanHandle`](go/internal/extractor/python.go#L31) | method | Reports whether the extractor supports a given file. |
| [`(e *PythonExtractor).Extract`](go/internal/extractor/python.go#L37) | method | Parses Python source and produces analysis output. |
| [`indentWidth`](go/internal/extractor/python.go#L138) | helper function | Computes indentation width for Python source lines. |
| [`peekDocstring`](go/internal/extractor/python.go#L153) | helper function | Reads ahead to identify a docstring candidate. |
| [`ExtractPythonFromReader`](go/internal/extractor/python.go#L188) | function | Extracts Python symbols directly from a reader. |

### Types

| Type | Shape | Description |
|---|---|---|
| [`PythonExtractor`](go/internal/extractor/python.go#L25) | `struct` | Concrete Python language extractor. |
| [`classFrame`](go/internal/extractor/python.go#L53) | `struct` | Internal stack frame used while walking nested classes. |

### Usage Example

```go
ext := extractor.NewPythonExtractor()
if ext.CanHandle("example.py") {
    result, err := ext.Extract("example.py", sourceReader)
    _ = result
    _ = err
}
```

## Shared Contract Types

The repository’s public API is built around a set of shared contract types in [`go/internal/models/contracts.go`](go/internal/models/contracts.go). These types are used by extractors, orchestrators, writers, and the server. For Python consumers, the most relevant types are the shape of extracted symbols and their relationships.

### Types

| Type | Shape | Description |
|---|---|---|
| [`LLMConfig`](go/internal/models/contracts.go#L6) | `struct` | Configuration for model/provider access. |
| [`Symbol`](go/internal/models/contracts.go#L53) | `struct` | Represents an extracted symbol, including its location and metadata. |
| [`Relationship`](go/internal/models/contracts.go#L64) | `struct` | Represents a relation between two symbols. |
| [`RationaleNote`](go/internal/models/contracts.go#L74) | `struct` | Stores explanatory note content attached to analysis. |
| [`AnalysisResult`](go/internal/models/contracts.go#L82) | `struct` | Top-level extraction/analysis result containing symbols and relationships. |
| [`Shard`](go/internal/models/contracts.go#L97) | `struct` | Describes a unit of repository work. |
| [`QAHistory`](go/internal/models/contracts.go#L104) | `struct` | Stores QA history records. |
| [`FileManifest`](go/internal/models/contracts.go#L111) | `struct` | Represents file inventory information. |
| [`WikiPageSpec`](go/internal/models/contracts.go#L119) | `struct` | Page specification used during synthesis. |
| [`WikiSection`](go/internal/models/contracts.go#L132) | `struct` | Section descriptor used by wiki generation. |
| [`WikiPlan`](go/internal/models/contracts.go#L139) | `struct` | Overall wiki generation plan. |
| [`ScanMeta`](go/internal/models/contracts.go#L147) | `struct` | Scan metadata associated with repository analysis. |

### Functions

| Function | Signature / Shape | Description |
|---|---|---|
| [`DefaultLLMConfig`](go/internal/models/contracts.go#L18) | constructor/helper | Returns the default LLM configuration. |

> **Sources:** `go/internal/models/contracts.go` · L6–L156 · [`LLMConfig`](go/internal/models/contracts.go#L6) · [`Symbol`](go/internal/models/contracts.go#L53) · [`Relationship`](go/internal/models/contracts.go#L64) · [`AnalysisResult`](go/internal/models/contracts.go#L82)

## Related Runtime Types Used by Python Extraction

The Python extractor does not operate in isolation; it emits the same shared runtime types used throughout the repository. These types are important for anyone consuming the Python-facing API because they define the result shape.

### Functions

| Function | Signature / Shape | Description |
|---|---|---|
| [`NewRegistry`](go/internal/extractor/extractor.go#L24) | constructor | Builds an extractor registry. |
| [`(r *Registry).ExtractFile`](go/internal/extractor/extractor.go#L37) | method | Dispatches file extraction to the correct language implementation. |
| [`MergeResults`](go/internal/extractor/extractor.go#L50) | function | Merges multiple extraction results into one combined result. |

### Types

| Type | Shape | Description |
|---|---|---|
| [`Extractor`](go/internal/extractor/extractor.go#L11) | `interface` | Common contract implemented by language extractors. |
| [`Registry`](go/internal/extractor/extractor.go#L19) | `struct` | Holds registered extractors. |

### Cross-Module Dependency Table

| Module | Imports From | Called By | Calls Into | Inherits From |
|--------|-------------|-----------|------------|---------------|
| `go/internal/extractor/python.go` | `go/internal/models/contracts.go` | `go/internal/extractor/extractor.go` | model population helpers; shared result types | `Extractor` |
| `go/internal/extractor/extractor.go` | extractor implementations, shared models | orchestrator code, tests | language-specific extractors | — |
| `go/internal/models/contracts.go` | — | extractor, orchestrator, storage, server, synthesis | data contracts across runtime | — |

> **Sources:** `go/internal/extractor/extractor.go` · L11–L68 · [`Extractor`](go/internal/extractor/extractor.go#L11) · [`Registry`](go/internal/extractor/extractor.go#L19) · [`MergeResults`](go/internal/extractor/extractor.go#L50)

## Storage and Persistence API

The storage layer is part of the runtime surface because it persists extracted symbols, relationships, wiki pages, and run metadata. The main entry point is [`Open`](go/internal/storage/store.go#L24), which returns a [`Store`](go/internal/storage/store.go#L18). Many higher-level components use storage through the public methods surfaced on [`Store`](go/internal/storage/store.go#L18) and the compatibility aliases in [`go/internal/storage/aliases.go`](go/internal/storage/aliases.go).

### Functions

| Function | Signature / Shape | Description |
|---|---|---|
| [`Open`](go/internal/storage/store.go#L24) | constructor | Opens a persistent store. |
| [`DefaultPath`](go/internal/storage/store.go#L38) | function | Returns the default storage path. |
| [`(s *Store).CreateRun`](go/internal/storage/store.go#L116) | method | Creates a new analysis run record. |
| [`(s *Store).SaveSymbols`](go/internal/storage/store.go#L149) | method | Persists extracted symbols. |
| [`(s *Store).SaveRelationships`](go/internal/storage/store.go#L200) | method | Persists extracted relationships. |
| [`(s *Store).UpsertWikiPage`](go/internal/storage/store.go#L247) | method | Inserts or updates a wiki page. |
| [`(s *Store).SaveQA`](go/internal/storage/store.go#L303) | method | Saves QA information. |
| [`(s *Store).UpsertManifest`](go/internal/storage/store.go#L314) | method | Persists a file manifest. |

### Types

| Type | Shape | Description |
|---|---|---|
| [`Store`](go/internal/storage/store.go#L18) | `struct` | Persistent storage handle. |
| [`WikiPageRow`](go/internal/storage/store.go#L292) | `struct` | Row representation for stored wiki pages. |

### Sources

> **Sources:** `go/internal/storage/store.go` · L18–L335 · [`Store`](go/internal/storage/store.go#L18) · [`Open`](go/internal/storage/store.go#L24) · [`(s *Store).SaveSymbols`](go/internal/storage/store.go#L149) · [`(s *Store).UpsertWikiPage`](go/internal/storage/store.go#L247)

## LLM Client and Token Accounting

The LLM client is a foundational runtime API that powers synthesis, enrichment, and question-answer flows. The main public type is [`Client`](go/internal/llm/client.go#L110), created by [`New`](go/internal/llm/client.go#L120). It exposes synchronous and streaming completion APIs through [`(c *Client).Call`](go/internal/llm/client.go#L161), [`(c *Client).CallWithRetry`](go/internal/llm/client.go#L166), and [`(c *Client).StreamCall`](go/internal/llm/client.go#L204). The same client also supports embeddings via [`(c *Client).Embed`](go/internal/llm/client.go#L234).

### Functions

| Function | Signature / Shape | Description |
|---|---|---|
| [`New`](go/internal/llm/client.go#L120) | constructor | Builds a configured LLM client. |
| [`inferBaseURL`](go/internal/llm/client.go#L148) | function | Derives the API base URL from configuration. |
| [`(c *Client).CallWithRetry`](go/internal/llm/client.go#L166) | method | Executes a retrying chat/completion request. |
| [`(c *Client).Embed`](go/internal/llm/client.go#L234) | method | Requests embeddings for input text. |
| [`buildMessages`](go/internal/llm/client.go#L344) | function | Constructs request messages from system/user inputs. |
| [`isTransient`](go/internal/llm/client.go#L357) | function | Classifies errors as retryable or not. |

### Types

| Type | Shape | Description |
|---|---|---|
| [`TokenStats`](go/internal/llm/client.go#L27) | `struct` | Tracks token usage counters. |
| [`Caller`](go/internal/llm/client.go#L82) | `interface` | Abstract LLM call interface. |
| [`FakeCaller`](go/internal/llm/client.go#L89) | `struct` | Test/dummy implementation of `Caller`. |
| [`Client`](go/internal/llm/client.go#L110) | `struct` | Concrete LLM client implementation. |

### Selected Methods

| Method | Signature / Shape | Description |
|---|---|---|
| [`(t *TokenStats).Add`](go/internal/llm/client.go#L35) | method | Adds counters into a running total. |
| [`(t *TokenStats).Summary`](go/internal/llm/client.go#L56) | method | Produces a formatted usage summary. |
| [`(f *FakeCaller).Call`](go/internal/llm/client.go#L96) | method | Returns a canned completion response. |
| [`(c *Client).StreamCall`](go/internal/llm/client.go#L204) | method | Streams a completion response. |
| [`(c *Client).Model`](go/internal/llm/client.go#L340) | method | Returns the configured model name. |

> **Sources:** `go/internal/llm/client.go` · L27–L385 · [`TokenStats`](go/internal/llm/client.go#L27) · [`Caller`](go/internal/llm/client.go#L82) · [`Client`](go/internal/llm/client.go#L110) · [`(c *Client).Embed`](go/internal/llm/client.go#L234)

## Orchestration and Synthesis API

The orchestration layer exposes the top-level runtime flows for asking questions, digesting shards, updating outputs, and planning wiki pages. These are public API shapes in practice because they are the canonical entry points used by commands and server handlers.

### Functions

| Function | Signature / Shape | Description |
|---|---|---|
| [`RunAsk`](go/internal/orchestrator/run_ask.go#L59) | function | Runs the question-answer flow. |
| [`StreamAsk`](go/internal/orchestrator/run_ask.go#L112) | function | Streams ask responses. |
| [`RunDigest`](go/internal/orchestrator/run_digest.go#L48) | function | Executes the digest pipeline over shards. |
| [`RunUpdate`](go/internal/orchestrator/run_update.go#L30) | function | Runs the update pipeline. |
| [`NewShardPlanner`](go/internal/orchestrator/sharding.go#L23) | constructor | Creates a shard planner. |
| [`(sp *ShardPlanner).Plan`](go/internal/orchestrator/sharding.go#L31) | method | Produces a sharding plan. |

### Types

| Type | Shape | Description |
|---|---|---|
| [`AskOptions`](go/internal/orchestrator/run_ask.go#L34) | `struct` | Options for ask flows. |
| [`AskResult`](go/internal/orchestrator/run_ask.go#L43) | `struct` | Result payload for ask flows. |
| [`DigestOptions`](go/internal/orchestrator/run_digest.go#L27) | `struct` | Options for digest runs. |
| [`UpdateOptions`](go/internal/orchestrator/run_update.go#L16) | `struct` | Options for update runs. |
| [`ShardPlanner`](go/internal/orchestrator/sharding.go#L17) | `struct` | Planner that groups files into shards. |
| [`Snapshotter`](go/internal/orchestrator/snapshotter.go#L57) | `struct` | Creates repository snapshots. |

### Notable Helpers

| Function | Signature / Shape | Description |
|---|---|---|
| [`tryRAGSearch`](go/internal/orchestrator/run_ask.go#L144) | function | Attempts retrieval-augmented search before answering. |
| [`buildContext`](go/internal/orchestrator/run_ask.go#L211) | function | Builds the context window for ask requests. |
| [`combineResults`](go/internal/orchestrator/run_digest.go#L346) | function | Merges per-shard results into a single response. |
| [`detectLanguage`](go/internal/orchestrator/snapshotter.go#L162) | function | Infers the language of a file. |
| [`fileTokenEstimate`](go/internal/orchestrator/sharding.go#L100) | function | Estimates token size for sharding. |

> **Sources:** `go/internal/orchestrator/run_ask.go` · L34–L261 · `go/internal/orchestrator/run_digest.go` · L27–L396 · `go/internal/orchestrator/run_update.go` · L16–L179 · `go/internal/orchestrator/sharding.go` · L17–L106

## RAG and Search-Primitives API

The repository exposes low-level retrieval primitives that can be used directly by internal callers. These are relevant to Python-facing analysis flows because they transform source files into chunks and searchable vectors.

### Functions

| Function | Signature / Shape | Description |
|---|---|---|
| [`ChunkFile`](go/internal/rag/chunker.go#L40) | function | Splits a file into searchable chunks. |
| [`WriteScanMeta`](go/internal/rag/scan_meta.go#L24) | function | Writes scan metadata to disk. |
| [`ReadScanMeta`](go/internal/rag/scan_meta.go#L39) | function | Reads scan metadata from disk. |
| [`PatchScanMeta`](go/internal/rag/scan_meta.go#L52) | function | Updates stored scan metadata. |
| [`NewVectorStore`](go/internal/rag/vector_store.go#L27) | constructor | Creates a vector store instance. |
| [`(v *VectorStore).Search`](go/internal/rag/vector_store.go#L71) | method | Searches stored chunks by similarity. |

### Types

| Type | Shape | Description |
|---|---|---|
| [`Chunk`](go/internal/rag/chunker.go#L11) | `struct` | Chunk record emitted by the chunker. |
| [`ScanMeta`](go/internal/rag/scan_meta.go#L12) | `struct` | Scan metadata persisted alongside embeddings. |
| [`VectorStore`](go/internal/rag/vector_store.go#L15) | `struct` | In-memory/persisted vector collection. |
| [`SearchResult`](go/internal/rag/vector_store.go#L21) | `struct` | Result item returned by vector search. |

> **Sources:** `go/internal/rag/chunker.go` · L11–L96 · `go/internal/rag/scan_meta.go` · L12–L81 · `go/internal/rag/vector_store.go` · L15–L118

## API Surface Summary

The table below highlights the central runtime symbols surfaced by the index for library consumers, with the strongest relevance to Python-related workflows.

| Package / Module | Central Symbols |
|---|---|
| `go/internal/extractor/python.go` | [`PythonExtractor`](go/internal/extractor/python.go#L25), [`NewPythonExtractor`](go/internal/extractor/python.go#L28), [`(e *PythonExtractor).Extract`](go/internal/extractor/python.go#L37), [`ExtractPythonFromReader`](go/internal/extractor/python.go#L188) |
| `go/internal/models/contracts.go` | [`Symbol`](go/internal/models/contracts.go#L53), [`Relationship`](go/internal/models/contracts.go#L64), [`AnalysisResult`](go/internal/models/contracts.go#L82), [`WikiPlan`](go/internal/models/contracts.go#L139) |
| `go/internal/extractor/extractor.go` | [`Extractor`](go/internal/extractor/extractor.go#L11), [`Registry`](go/internal/extractor/extractor.go#L19), [`NewRegistry`](go/internal/extractor/extractor.go#L24), [`MergeResults`](go/internal/extractor/extractor.go#L50) |
| `go/internal/storage/store.go` | [`Store`](go/internal/storage/store.go#L18), [`Open`](go/internal/storage/store.go#L24), [`(s *Store).SaveSymbols`](go/internal/storage/store.go#L149), [`(s *Store).ListWikiPages`](go/internal/storage/store.go#L270) |
| `go/internal/llm/client.go` | [`Client`](go/internal/llm/client.go#L110), [`New`](go/internal/llm/client.go#L120), [`(c *Client).CallWithRetry`](go/internal/llm/client.go#L166), [`(c *Client).Embed`](go/internal/llm/client.go#L234) |

> **Sources:** `go/internal/extractor/python.go` · `go/internal/models/contracts.go` · `go/internal/extractor/extractor.go` · `go/internal/storage/store.go` · `go/internal/llm/client.go`