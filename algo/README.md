# rekipedia — Algorithm Reference

This folder documents the core algorithms powering rekipedia's codebase intelligence engine.
Each file maps to a specific subsystem with complexity analysis, design rationale, and known trade-offs.

## Index

| File | Subsystem | Key Algorithm |
|---|---|---|
| [bm25-symbol-search.md](bm25-symbol-search.md) | Cross-repo search | BM25-inspired token scoring |
| [graph-analysis.md](graph-analysis.md) | Dependency graph | Degree centrality, knowledge gap detection |
| [impact-analysis.md](impact-analysis.md) | Blast radius | BFS reverse dependency traversal |
| [rag-embedder.md](rag-embedder.md) | Semantic search | MMR (Maximal Marginal Relevance) + FAISS |
| [sharding.md](sharding.md) | Scan orchestration | Token-budget greedy bin-packing |
| [incremental-update.md](incremental-update.md) | `reki update` | SHA-256 diff + carry-forward |
| [agentic-ask.md](agentic-ask.md) | `reki ask` | ReAct tool-calling loop |
| [wiki-planner.md](wiki-planner.md) | Wiki generation | LLM-driven structure planning |
