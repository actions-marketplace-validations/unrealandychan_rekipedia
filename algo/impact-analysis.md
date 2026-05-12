# Impact / Blast-Radius Analysis

**Source:** `src/rekipedia/analysis/impact.py`
**Used by:** `reki ask "what breaks if I change X?"`, MCP tool `get_impact`

## Overview

Given a target file, computes which other symbols and files are transitively affected — the "blast radius" of a change.

## Algorithm — BFS on Reverse Call Graph

```
Input:  target_file, relationships, symbols, depth=2

1. Build sym_by_file:  file → [symbol names]
2. Build sym_file:     symbol name → file
3. Build reverse graph: for each "calls" rel (A calls B):
       reverse[B].append(A)   # B is called by A

4. Seed = all symbols defined in target_file

5. BFS from seeds through reverse graph up to `depth` hops:
   visited = {seed symbols}
   queue   = [(seed, 0)]
   while queue:
       sym, d = dequeue
       if d >= depth: skip
       for caller in reverse[sym]:
           if caller not in visited:
               visited.add(caller), enqueue(caller, d+1)

6. Output:
   affected_symbols = visited - seeds
   affected_files   = {sym_file[s] for s in affected_symbols}
   related_tests    = {f for f in affected_files if "test" in f}
```

## Complexity

| Phase | Complexity |
|---|---|
| Build maps | O(S + E) — symbols + relationships |
| BFS | O(V + E) where V = visited nodes |
| Total | O(S + E) |

With `depth=2`, the BFS is effectively bounded and very fast even on large codebases.

## Parameters

| Param | Default | Effect |
|---|---|---|
| `depth` | 2 | How many hops to traverse (exponential blast radius growth) |

**Warning:** `depth=3+` can return the entire call graph for highly connected repos. Consider adding a `max_affected` cap.

## Known Limitations

| Limitation | Detail |
|---|---|
| Only `"calls"` edges | Ignores `"imports"`, `"inherits"`, `"uses"` relationships |
| No transitive imports | File-level dependencies via `import` not modelled |
| Test detection | Only checks `"test" in filename` (same weakness as graph_analysis.py) |

## Integration Points

- MCP tool: `get_impact(target_file, depth=2)`
- `reki ask` agent can call this via `get_relationships(target)` tool
- Output surfaced in `architecture-overview` wiki page
