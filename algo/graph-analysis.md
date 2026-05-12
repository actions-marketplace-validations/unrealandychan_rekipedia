# Graph Analysis Algorithms

**Source:** `src/rekipedia/analysis/graph_analysis.py`
**Used by:** `reki scan`, hub-node detection, knowledge gap reporting

## 1. God Node / Hub Detection (Degree Centrality)

Identifies symbols that are heavily connected — high fan-in/fan-out (the "god objects" or critical hubs).

### Algorithm

```python
degree: dict[str, int] = defaultdict(int)
for rel in relationships:
    degree[rel.from_] += 1   # out-degree
    degree[rel.to] += 1      # in-degree

sorted_nodes = sorted(degree.items(), key=lambda x: x[1], reverse=True)
return sorted_nodes[:top_n]
```

**Metric:** combined in+out degree (a proxy for betweenness centrality, O(N) instead of O(N³))

| Approach | Complexity | Quality |
|---|---|---|
| Degree centrality (current) | O(E) | Good approximation |
| Betweenness centrality (networkx) | O(V × E) | Exact but slow for large graphs |

**Design rationale:** avoids `networkx` dependency for large graphs while still identifying the most connected nodes with high accuracy in practice.

## 2. Knowledge Gap Detection

Finds symbols that are called frequently but have **no test coverage** — the riskiest untested code.

### Algorithm

```
Step 1: Build call-count map
  call_count[to] += 1  for every "calls" relationship

Step 2: Build test-coverage set
  test_covered.add(to) if caller is a test_ function or lives in /test/

Step 3: Find gaps
  for each symbol with call_count ≥ 3:
    if symbol not in test_covered:
      yield as knowledge gap
```

**Threshold:** call_count ≥ 3 (configurable — currently hardcoded)

**Output:** top 20 gaps sorted by call_count descending.

### Trade-offs

| Aspect | Current | Improvement |
|---|---|---|
| Test detection | `name.startswith("test_")` or `"/test" in file` | Parse `@pytest.mark` decorators, `unittest.TestCase` subclasses |
| Threshold | Hardcoded `3` | Expose as `REKIPEDIA_GAP_MIN_CALLS` env var |
| Result cap | Hardcoded `20` | Configurable |

## 3. Hub Nodes (Betweenness Approximation)

`_build_hub_nodes()` uses degree as a proxy for betweenness — same rationale as §1.

**Algorithm:** identical to god-node detection but applied to the full graph rather than relationships only.

## Integration Points

- Results stored in SQLite via `SqliteStore`
- Surfaced in wiki page `technical-debt` (importance: 70)
- Accessible via `reki ask "which symbols have no test coverage?"`
