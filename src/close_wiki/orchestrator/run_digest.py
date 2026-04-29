"""Main orchestration pipeline for `close-wiki scan`.

Flow:
    1. Snapshot repo → list[FileManifest]
    2. Shard files → list[Shard]
    3. For each shard → run extractor (Docker or local) → AnalysisResult
    4. Persist symbols / relationships to SQLite
    5. Synthesise wiki pages via LLM (host-side)
    6. Build Mermaid diagrams
    7. Export markdown + JSON
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Callable

from close_wiki.models.contracts import AnalysisResult, LLMConfig
from close_wiki.orchestrator.sharding import ShardPlanner
from close_wiki.orchestrator.snapshotter import Snapshotter
from close_wiki.sandbox.runner import BaseRunner, get_runner
from close_wiki.storage.sqlite_store import SqliteStore


def run_digest(
    repo_root: Path,
    output_dir: Path,
    llm_config: LLMConfig | None = None,
    *,
    force_local: bool = False,
    progress: Callable[[str], None] | None = None,
) -> None:
    """Full scan pipeline.

    Args:
        repo_root: Absolute path to the repository to scan.
        output_dir: `.close-wiki/` directory; DB + wiki output goes here.
        llm_config: LLM settings; defaults to LLMConfig() which uses ollama/llama4.
        force_local: Skip Docker even if available.
        progress: Optional callback that receives status strings for display.
    """
    llm_config = llm_config or LLMConfig()
    _log = progress or (lambda _: None)

    run_id = str(uuid.uuid4())
    db_path = output_dir / "store.db"

    store = SqliteStore(db_path)
    store.open()

    try:
        store.upsert_run(run_id, str(repo_root))
        _log(f"Run {run_id[:8]} started")

        # ── 1. Snapshot ──────────────────────────────────────────────
        _log("Snapshotting repository…")
        snapshotter = Snapshotter(repo_root)
        files = snapshotter.snapshot()
        _log(f"  {len(files)} files found")

        store.upsert_snapshot(run_id, [f.model_dump() for f in files])
        for f in files:
            store.upsert_file(run_id, f.path, f.sha256, f.size_bytes, f.language)

        # ── 2. Shard ─────────────────────────────────────────────────
        _log("Planning shards…")
        planner = ShardPlanner()
        shards = planner.plan(files, llm_config)
        _log(f"  {len(shards)} shards")

        # ── 3. Extract ───────────────────────────────────────────────
        runner: BaseRunner = get_runner(force_local=force_local)
        runner_name = type(runner).__name__
        _log(f"Using {runner_name}")

        merged_results: list[AnalysisResult] = []
        for i, shard in enumerate(shards, 1):
            _log(f"  Extracting shard {i}/{len(shards)}: {shard.shard_id}")
            result = runner.run(shard, repo_root)
            merged_results.append(result)

            # Persist
            symbols_dicts = [s.model_dump() for s in result.symbols]
            rels_dicts = [r.model_dump(by_alias=True) for r in result.relationships]
            store.upsert_symbols(run_id, symbols_dicts)
            store.upsert_relationships(run_id, rels_dicts)

        # ── 4. Synthesise wiki pages ─────────────────────────────────
        _log("Synthesising wiki pages…")
        from close_wiki.synthesis.page_builder import PageBuilder  # noqa: PLC0415
        from close_wiki.synthesis.diagram_builder import DiagramBuilder  # noqa: PLC0415

        all_symbols_raw = store.get_all_symbols(run_id)
        print(f"Total symbols: {len(all_symbols_raw)}")
        all_rels_raw = store.get_all_relationships(run_id)

        combined = _combine_results(merged_results)
        builder = PageBuilder(llm_config)
        pages = builder.build(combined)

        diagram_builder = DiagramBuilder()
        diagrams = diagram_builder.build(all_rels_raw)

        for slug, (title, content) in pages.items():
            store.upsert_page(run_id, slug, title, content)
        for name, (dtype, content) in diagrams.items():
            store.upsert_diagram(run_id, name, dtype, content)

        # ── 5. Export ────────────────────────────────────────────────
        _log("Exporting…")
        from close_wiki.exporters.markdown_export import MarkdownExporter  # noqa: PLC0415
        from close_wiki.exporters.json_export import JsonExporter  # noqa: PLC0415

        MarkdownExporter(output_dir).export(pages, diagrams)
        JsonExporter(output_dir).export(run_id, files, combined, pages, diagrams)

        store.update_run_status(run_id, "success")
        _log("Done.")

    except Exception:
        store.update_run_status(run_id, "failed")
        raise
    finally:
        store.close()


def _combine_results(results: list[AnalysisResult]) -> AnalysisResult:
    if not results:
        return AnalysisResult(shard_id="all", files_seen=[], entry_points=[])

    combined = AnalysisResult(shard_id="all", files_seen=[], entry_points=[])
    for r in results:
        combined.files_seen.extend(r.files_seen)
        combined.entry_points.extend(r.entry_points)
        combined.symbols.extend(r.symbols)
        combined.relationships.extend(r.relationships)
        combined.build_commands.extend(r.build_commands)
        combined.test_commands.extend(r.test_commands)
        combined.risks.extend(r.risks)
        combined.evidence.update(r.evidence)
    return combined
