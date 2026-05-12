# Incremental Update — SHA-256 Diff + Carry-Forward

**Source:** `src/rekipedia/orchestrator/run_update.py`
**Used by:** `reki update`

## Overview

`reki update` avoids re-scanning unchanged files by diffing file hashes against the last run. Only changed files are re-extracted; unchanged symbols are carried forward from the previous run.

## Pipeline

```
1. Load last successful run_id from SQLite
   └─ If none → fall back to full reki scan

2. Snapshot current repo → {file: sha256}
3. Diff against stored hashes from last run:
   changed_files = {f | sha256(f) ≠ stored_hash(f)}
   unchanged_files = all_files − changed_files

4. If changed_files is empty → report "up-to-date", exit early

5. Create new run_id (UUID)

6. Re-extract changed_files only:
   ShardPlanner → shards of changed files
   ThreadPoolExecutor → LLM extraction per shard
   → new symbols + relationships for changed files

7. Carry forward from last run:
   symbols for unchanged_files → copy to new run_id
   relationships for unchanged_files → copy to new run_id

8. Re-synthesise ALL wiki pages (always — full context needed)
   (even unchanged files may affect architecture-overview etc.)

9. Export markdown + JSON
```

## Why Always Re-synthesise Wiki Pages?

Wiki pages describe the **whole system** (architecture, data flow, component relationships). A small change in one file can affect how the overview is described. Re-running page synthesis is cheap compared to extraction (no Docker, smaller prompts).

## Hash Storage

File hashes are stored in SQLite (`FileManifest` table) alongside the `run_id`. Each run stores a complete snapshot so rollback/diff is always possible.

## Complexity

| Phase | Complexity |
|---|---|
| Snapshot | O(F × file_read) — stat + sha256 |
| Diff | O(F) |
| Re-extract | O(C × extraction_cost) — C changed files |
| Carry-forward | O(U) — U unchanged symbols |
| Wiki synthesis | O(P × page_cost) — P wiki pages |

For a repo with 200 files where 5 changed: ~97.5% extraction work saved.

## Edge Cases

| Case | Behaviour |
|---|---|
| File deleted | Removed from symbol index; relationships cleaned up |
| File added | Treated as changed (new sha256 not in store) |
| Rename | Old path treated as deleted, new path as added |
| Empty change set | Early exit — no LLM calls made |
| No previous scan | Full `run_digest()` fallback |

## Integration Points

- CLI: `reki update /path/to/repo`
- Called by watcher daemon (`watcher.py`) on filesystem events
- `Snapshotter` class handles the file discovery + hashing
