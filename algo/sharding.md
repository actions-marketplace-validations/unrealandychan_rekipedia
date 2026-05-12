# Sharding — Token-Budget Greedy Bin-Packing

**Source:** `src/rekipedia/orchestrator/sharding.py`
**Used by:** `reki scan`, `reki update`

## Overview

Before sending source files to the LLM for symbol extraction, rekipedia partitions them into **shards** — groups of files that fit within a token budget. This prevents context overflow and enables parallel processing.

## Algorithm — Greedy First-Fit (Directory-Grouped)

```
Input: list[FileManifest] (path + size_bytes), token_budget

Phase 1 — Group by top-level directory:
    groups["src"]  = [file1, file2, ...]
    groups["tests"] = [file3, ...]
    groups["."]    = [root files]

Phase 2 — Greedy bin-pack within each group:
    bucket = []
    bucket_tokens = 0

    for file in group:
        file_tokens = max(1, file.size_bytes // BYTES_PER_TOKEN)
        if bucket AND bucket_tokens + file_tokens > budget:
            emit Shard(bucket)
            bucket = [], bucket_tokens = 0
        bucket.append(file)
        bucket_tokens += file_tokens

    if bucket: emit Shard(bucket)
```

**Token estimation:** `size_bytes // BYTES_PER_TOKEN` (4 bytes ≈ 1 token for code). Fast O(1) approximation — avoids running a tokeniser on every file.

## Shard Naming

```
group_dir          → shard_id = "src"
group_dir + split  → shard_id = "src#1", "src#2", ...
```

## Complexity

| Phase | Complexity |
|---|---|
| Grouping | O(F) — F files |
| Bin-packing | O(F) — one pass |
| Total | O(F) |

## Configuration

| Variable | Default | Effect |
|---|---|---|
| `REKIPEDIA_SHARD_TOKEN_BUDGET` | (see source) | Max tokens per shard |

## Why Directory Grouping First?

Files in the same directory tend to be semantically related (same module). Keeping them in the same shard improves extraction quality — the LLM sees related symbols together and can infer cross-file relationships within the shard.

## Trade-offs

| Aspect | Current | Alternative |
|---|---|---|
| Token estimation | `size_bytes / 4` | tiktoken for exact counts (slower) |
| File ordering | Filesystem order | Sort by size (large-first for better packing) |
| Cross-dir splitting | Hard boundary at dir | Allow cross-dir packing for small dirs |
| Oversized single file | Gets its own shard | Could split file at line boundaries |

## Integration Points

- `ShardPlanner.plan(files, llm)` called in `run_digest.py` before parallel extraction
- Shards processed by `ThreadPoolExecutor` with `_MAX_SHARD_WORKERS=4`
- Each shard → one LLM extraction call → `AnalysisResult` (symbols + relationships)
