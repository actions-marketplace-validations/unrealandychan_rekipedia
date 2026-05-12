# BM25 Symbol Search

**Source:** `src/rekipedia/analysis/cross_repo_search.py`
**Used by:** `reki search`, cross-repo fan-out queries

## Overview

rekipedia implements a lightweight BM25-inspired scorer for symbol-name search — **no external search library required**. It runs entirely in-process against the SQLite symbol index.

## Algorithm

### Step 1 — Tokenisation

```python
def _tokenize_symbol(name: str) -> list[str]:
    tokens = name.replace('-', '_').split('_')          # snake_case split
    for t in tokens:
        parts = re.sub(r'([A-Z][a-z]+|...)', r'\1 ', t) # camelCase split
    return [p.lower() for p in parts]
```

Handles both `snake_case` and `camelCase` identifiers. Output: lowercased token list.

**Example:**
- `compute_god_nodes` → `["compute", "god", "nodes"]`
- `ShardPlanner` → `["shard", "planner"]`

### Step 2 — BM25 Scoring

```
score = Σ IDF(t) × TF(t, d) × (k1 + 1) / (TF(t, d) + k1 × (1 - b + b × |d| / avgdl))
```

Parameters used:
| Param | Value | Meaning |
|---|---|---|
| `k1` | 1.5 | Term frequency saturation |
| `b` | 0.75 | Document length normalisation |
| `avgdl` | 5.0 | Average symbol name length (tokens) |
| `IDF` | 1.0 | Simplified (no corpus-level IDF) |

> **Note:** IDF is hardcoded to `1.0` — a known simplification. Real BM25 would compute IDF per token across the corpus. This is a potential improvement area (see [Trade-offs](#trade-offs)).

### Step 3 — Fan-out (Cross-repo)

```python
with ThreadPoolExecutor(max_workers=min(len(db_paths), 8)) as pool:
    futures = {pool.submit(_search_single_repo, db, query, kind): db for db in db_paths}
```

Each registered repo's SQLite DB is searched in parallel. Results are merged and re-ranked by score globally (top 200 returned).

## Complexity

| Phase | Complexity |
|---|---|
| Tokenise | O(L) — symbol name length |
| Score one symbol | O(Q) — query token count |
| Score all symbols | O(N × Q) — N symbols in index |
| Fan-out | O(R × N × Q / workers) — R repos |

For a typical repo with 5,000 symbols and 3-token queries: ~15K ops per repo, effectively instant.

## Trade-offs

| Aspect | Current | Better Alternative |
|---|---|---|
| IDF | Hardcoded `1.0` | Precompute per-corpus IDF at scan time |
| Scope | Symbol names only | Include docstrings / file paths |
| Ranking merge | Global re-sort | Reciprocal Rank Fusion (RRF) |
| Kind filter | Post-fetch | Pre-filter in SQL `WHERE kind = ?` |

## Integration Points

- Called by CLI `reki search <query>`
- Feeds into `agent_ask.py` tool `search_code()` as a fallback when RAG index is unavailable
