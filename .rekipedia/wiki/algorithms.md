---
slug: algorithms
title: "Algorithms"
section: internals
tags: [internals, algorithms]
pin: false
importance: 50
created_at: 2026-05-05T03:45:09Z
rekipedia_version: 0.10.1
---

# Algorithms

## Overview

This document provides a detailed overview of the algorithms used in the project. The algorithms are implemented across various modules and serve different purposes, including graph analysis, cross-repository search, impact analysis, and refactor detection. Each section will cover key algorithms, their implementation details, and performance considerations.

## Key Algorithms

### BM25-Inspired Scoring

The BM25-inspired scoring algorithm is implemented in the function [`_score_bm25`](src/rekipedia/analysis/cross_repo_search.py#L18). This algorithm is used for scoring search results based on their relevance to a query. It is a simplified version of the BM25 ranking function, which is widely used in information retrieval.

### God Node Detection

The function [`compute_god_nodes`](src/rekipedia/analysis/graph_analysis.py#L11) is responsible for detecting "god nodes" in a graph. These are nodes with a high degree of connectivity, indicating that they are central to the graph's structure. The algorithm computes the in-degree and out-degree for each node and returns the top N nodes sorted by their degree.

### Knowledge Gap Detection

The function [`_build_knowledge_gaps`](src/rekipedia/analysis/graph_analysis.py#L37) identifies symbols with high call counts but no test coverage. This algorithm helps in detecting areas of the codebase that are critical but lack sufficient testing.

### Impact Analysis

The function [`compute_impact`](src/rekipedia/analysis/impact.py#L6) performs a breadth-first search (BFS) from a target file through the reverse dependency graph. It returns the affected files, symbols, and related tests, helping developers understand the impact of changes in the codebase.

### Refactor Detection

Several functions in the module `refactor_detector.py` are dedicated to detecting various refactor issues:
- [`detect_god_nodes`](src/rekipedia/analysis/refactor_detector.py#L83)
- [`detect_circular_deps`](src/rekipedia/analysis/refactor_detector.py#L134)
- [`detect_dead_code`](src/rekipedia/analysis/refactor_detector.py#L199)
- [`detect_high_fan_in`](src/rekipedia/analysis/refactor_detector.py#L229)
- [`detect_high_fan_out`](src/rekipedia/analysis/refactor_detector.py#L266)
- [`detect_deep_inheritance`](src/rekipedia/analysis/refactor_detector.py#L303)

These functions analyze the codebase to identify potential refactor opportunities, such as god classes, circular dependencies, dead code, high fan-in/fan-out, and deep inheritance chains.

## Implementation Details

### BM25-Inspired Scoring

The BM25-inspired scoring algorithm is implemented as follows:

```python
def _score_bm25(query_tokens, symbol_tokens):
    """
    Simple BM25-inspired scoring without external deps.
    """
    # Implementation details...
```

This function takes two arguments: `query_tokens` and `symbol_tokens`. It computes a relevance score based on the frequency of query tokens in the symbol tokens.

### God Node Detection

The god node detection algorithm is implemented in the function `compute_god_nodes`:

```python
def compute_god_nodes(relationships, top_n):
    """
    Compute in+out degree for each symbol name and return top_n sorted by degree.
    """
    # Implementation details...
```

This function takes a list of relationships and the number of top nodes to return. It calculates the degree for each node and sorts them to find the top N nodes.

### Knowledge Gap Detection

The knowledge gap detection algorithm is implemented in the function `_build_knowledge_gaps`:

```python
def _build_knowledge_gaps(combined):
    """
    Detect symbols with high call counts but no test coverage.
    """
    # Implementation details...
```

This function takes an `AnalysisResult` object and identifies symbols with high call counts but no associated test coverage.

### Impact Analysis

The impact analysis algorithm is implemented in the function `compute_impact`:

```python
def compute_impact(target_file, relationships, symbols, depth):
    """
    BFS from target_file through reverse dependency graph.
    Returns affected_files, affected_symbols, related_tests.
    """
    # Implementation details...
```

This function performs a BFS from the target file through the reverse dependency graph to determine the impact of changes.

### Refactor Detection

The refactor detection algorithms are implemented in various functions in the `refactor_detector.py` module. For example, the function `detect_god_nodes` is implemented as follows:

```python
def detect_god_nodes(relationships, symbols, config):
    """
    Detect god classes/functions: top ``config.god_node_top_pct`` by total degree.
    """
    # Implementation details...
```

Each function in this module focuses on detecting a specific type of refactor issue, such as god nodes, circular dependencies, dead code, high fan-in/fan-out, and deep inheritance chains.

## Performance Considerations

### BM25-Inspired Scoring

The BM25-inspired scoring algorithm is designed to be lightweight and efficient. It avoids external dependencies and focuses on simplicity. However, it may not be as accurate as the full BM25 algorithm used in advanced search engines.

### God Node Detection

The god node detection algorithm relies on computing the degree of each node in the graph. This operation is generally efficient, but the performance can degrade for very large graphs. Optimizations such as parallel processing can be considered for handling large datasets.

### Knowledge Gap Detection

The knowledge gap detection algorithm involves analyzing call counts and test coverage. This process can be computationally intensive, especially for large codebases with extensive relationships. Caching intermediate results and using efficient data structures can help improve performance.

### Impact Analysis

The impact analysis algorithm uses BFS, which is efficient for most use cases. However, the performance can be affected by the depth of the search and the size of the dependency graph. Limiting the depth and optimizing the graph traversal can help mitigate performance issues.

### Refactor Detection

The refactor detection algorithms involve analyzing various aspects of the codebase, such as dependencies, call counts, and inheritance chains. These analyses can be computationally intensive, especially for large codebases. Using efficient algorithms and data structures, as well as parallel processing, can help improve performance.

## Sources

> **Sources:** `src/rekipedia/analysis/cross_repo_search.py` · L18–L32 · [`_score_bm25`](src/rekipedia/analysis/cross_repo_search.py#L18)  
> **Sources:** `src/rekipedia/analysis/graph_analysis.py` · L11–L34 · [`compute_god_nodes`](src/rekipedia/analysis/graph_analysis.py#L11)  
> **Sources:** `src/rekipedia/analysis/graph_analysis.py` · L37–L103 · [`_build_knowledge_gaps`](src/rekipedia/analysis/graph_analysis.py#L37)  
> **Sources:** `src/rekipedia/analysis/impact.py` · L6–L60 · [`compute_impact`](src/rekipedia/analysis/impact.py#L6)  
> **Sources:** `src/rekipedia/analysis/refactor_detector.py` · L83–L131 · [`detect_god_nodes`](src/rekipedia/analysis/refactor_detector.py#L83)  
> **Sources:** `src/rekipedia/analysis/refactor_detector.py` · L134–L196 · [`detect_circular_deps`](src/rekipedia/analysis/refactor_detector.py#L134)  
> **Sources:** `src/rekipedia/analysis/refactor_detector.py` · L199–L226 · [`detect_dead_code`](src/rekipedia/analysis/refactor_detector.py#L199)  
> **Sources:** `src/rekipedia/analysis/refactor_detector.py` · L229–L263 · [`detect_high_fan_in`](src/rekipedia/analysis/refactor_detector.py#L229)  
> **Sources:** `src/rekipedia/analysis/refactor_detector.py` · L266–L300 · [`detect_high_fan_out`](src/rekipedia/analysis/refactor_detector.py#L266)  
> **Sources:** `src/rekipedia/analysis/refactor_detector.py` · L303–L356 · [`detect_deep_inheritance`](src/rekipedia/analysis/refactor_detector.py#L303)