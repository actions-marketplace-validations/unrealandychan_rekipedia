# RAG Embedder — Semantic Search

**Source:** `src/rekipedia/rag/embedder.py`
**Used by:** `reki embed`, `reki ask` (hybrid search)

## Overview

Chunks source files, embeds them via litellm, persists a FAISS flat L2 index, and serves top-K results with **Maximal Marginal Relevance (MMR)** re-ranking to reduce redundant results.

## Pipeline

```
Source files
    ↓ chunk() — sliding window (overlap)
Chunks (text + metadata)
    ↓ embed() — litellm / OpenAI / Ollama
Float vectors
    ↓ FAISS IndexFlatL2.add()
FAISS index (index.faiss)
    + chunks.json (parallel metadata)
    + embed_meta.json (model info)
```

## 1. Chunking Strategy

Files are split into overlapping windows. Chunk metadata includes: `file`, `start_line`, `end_line`, `lang`.

**Overlap** prevents context loss at chunk boundaries (important for function signatures that span chunk edges).

## 2. Embedding

Uses litellm as a universal adapter — supports OpenAI, Anthropic, Ollama, LiteLLM proxy.

**Pitfall:** litellm adds `encoding_format: base64` automatically, which breaks some proxies. Fixed by using raw `httpx.post()` when `embed_base_url` is set (see skill pitfalls).

## 3. MMR Re-ranking

Standard FAISS search returns the top-K most similar chunks — but they tend to be **near-duplicates** (e.g. 5 chunks from the same function). MMR diversifies results.

### Formula

```
MMR(c) = λ × sim(query, c) − (1−λ) × max_{s∈Selected} sim(c, s)
```

### Implementation

```python
def _mmr(query_vec, candidate_vecs, top_k, lambda_=0.5):
    q = normalise(query_vec)
    cands = normalise(candidate_vecs)
    query_sims = cands @ q           # cosine similarity to query

    selected = []
    for _ in range(top_k):
        if not selected:
            idx = argmax(query_sims)  # first: best match
        else:
            redundancy = (cands @ cands[selected].T).max(axis=1)
            mmr_score  = λ × query_sims − (1−λ) × redundancy
            mmr_score[selected] = -∞   # mask already picked
            idx = argmax(mmr_score)
        selected.append(idx)
    return selected
```

**λ = 0.5** balances relevance vs diversity equally. Higher λ → more relevant but redundant. Lower λ → more diverse but less focused.

### Complexity

| Phase | Complexity |
|---|---|
| FAISS search | O(N × D) — N chunks, D dimensions |
| MMR iteration | O(K × N) — K selections |
| Total | O(N × (D + K)) |

For N=10,000 chunks, D=1536, K=8: ~15M ops — runs in milliseconds with numpy.

## Fallback (no FAISS)

When `faiss` is unavailable (e.g. arm64/M1 pip issues), falls back to **numpy brute-force cosine search**:

```python
scores = (embeddings @ query_vec) / (norms × query_norm)
top_k_indices = np.argsort(scores)[-top_k:][::-1]
```

O(N × D) — same asymptotic cost as FAISS flat index, just slower constant factor.

## Storage Layout

```
.rekipedia/rag/
    index.faiss      — FAISS IndexFlatL2
    chunks.json      — [{file, start_line, end_line, text, lang}, ...]
    embed_meta.json  — {model, dimension, timestamp, chunk_count}
```

## Integration Points

- `EmbedPipeline.search(query, top_k=8)` — used by `agent_ask.py` tool `search_code()`
- Built by `reki embed .` (separate from scan — optional step)
- Hybrid search: BM25 symbol search (always available) + RAG (when index exists)
