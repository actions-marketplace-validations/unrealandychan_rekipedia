"""Main orchestration pipeline for `close-wiki scan`.

Flow:
    1. Snapshot repo → list[FileManifest]
    2. Shard files → list[Shard]
    3. For each shard → run extractor (Docker or local) → AnalysisResult
    4. Build diagrams (used by architecture page)
    5. Synthesise wiki pages via LLM (host-side)
    6. Export markdown + JSON
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Callable

from close_wiki.models.contracts import AnalysisResult, LLMConfig
from close_wiki.orchestrator.sharding import ShardPlanner
from close_wiki.orchestrator.snapshotter import Snapshotter
from close_wiki.sandbox.runner import BaseRunner, get_runner
from close_wiki.storage.sqlite_store import SqliteStore

logger = logging.getLogger("close_wiki")


def run_digest(
    repo_root: Path,
    output_dir: Path,
    llm_config: LLMConfig | None = None,
    *,
    force_local: bool = False,
    verbose: bool = False,
    progress: Callable[[str], None] | None = None,
) -> None:
    """Full scan pipeline.

    Args:
        repo_root: Absolute path to the repository to scan.
        output_dir: `.close-wiki/` directory; DB + wiki output goes here.
        llm_config: LLM settings; defaults to LLMConfig() which uses ollama/llama4.
        force_local: Skip Docker even if available.
        verbose: Enable debug logging (litellm, HTTP, stack traces).
        progress: Optional callback that receives status strings for display.
    """
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        logging.getLogger("close_wiki").setLevel(logging.DEBUG)
        logging.getLogger("LiteLLM").setLevel(logging.DEBUG)
        logging.getLogger("httpx").setLevel(logging.DEBUG)
        import litellm
        litellm._turn_on_debug()  # type: ignore[attr-defined]
        logger.debug("Verbose mode ON — all debug logs enabled")
    else:
        logging.basicConfig(level=logging.WARNING)

    from tqdm import tqdm  # noqa: PLC0415

    llm_config = llm_config or LLMConfig()
    _log = progress or (lambda _: None)

    def _vlog(msg: str) -> None:
        """Log to both progress callback and verbose logger."""
        _log(msg)
        logger.debug(msg)

    run_id = str(uuid.uuid4())
    db_path = output_dir / "store.db"

    store = SqliteStore(db_path)
    store.open()

    try:
        store.upsert_run(run_id, str(repo_root))
        _vlog(f"Run {run_id[:8]} started")

        # ── 1. Snapshot ──────────────────────────────────────────────
        _vlog("Snapshotting repository…")
        snapshotter = Snapshotter(repo_root)
        files = snapshotter.snapshot()
        _vlog(f"  {len(files)} files found")

        store.upsert_snapshot(run_id, [f.model_dump() for f in files])
        for f in files:
            store.upsert_file(run_id, f.path, f.sha256, f.size_bytes, f.language)

        # ── 2. Shard ─────────────────────────────────────────────────
        _vlog("Planning shards…")
        planner = ShardPlanner()
        shards = planner.plan(files, llm_config)
        _vlog(f"  {len(shards)} shards planned")

        # ── 3. Extract ───────────────────────────────────────────────
        runner: BaseRunner = get_runner(force_local=force_local)
        runner_name = type(runner).__name__
        _vlog(f"Using {runner_name}")

        merged_results: list[AnalysisResult] = []
        shard_bar = tqdm(
            shards,
            desc="🔍 Extracting shards",
            unit="shard",
            dynamic_ncols=True,
            leave=True,
        )
        for shard in shard_bar:
            shard_bar.set_postfix(id=shard.shard_id[:12])
            _vlog(f"  Extracting shard: {shard.shard_id}")
            try:
                result = runner.run(shard, repo_root)
            except Exception as exc:
                logger.error("Shard %s failed: %s", shard.shard_id, exc, exc_info=verbose)
                raise
            merged_results.append(result)

            symbols_dicts = [s.model_dump() for s in result.symbols]
            rels_dicts = [r.model_dump(by_alias=True) for r in result.relationships]
            store.upsert_symbols(run_id, symbols_dicts)
            store.upsert_relationships(run_id, rels_dicts)
            _vlog(f"  → {len(result.symbols)} symbols, {len(result.relationships)} relationships")

        shard_bar.close()

        # ── 4. Build diagrams first (used by architecture page) ──────
        _vlog("Building diagrams…")
        _log("Building diagrams…")
        from close_wiki.synthesis.diagram_builder import DiagramBuilder  # noqa: PLC0415

        all_symbols_raw = store.get_all_symbols(run_id)
        all_rels_raw = store.get_all_relationships(run_id)
        _vlog(f"  Total symbols: {len(all_symbols_raw)}, relationships: {len(all_rels_raw)}")

        combined = _combine_results(merged_results)
        diagram_builder = DiagramBuilder()
        diagrams = diagram_builder.build(all_rels_raw, entry_points=combined.entry_points)
        _vlog(f"  Built {len(diagrams)} diagram(s): {list(diagrams.keys())}")

        combined.evidence["pre_built_module_graph"] = diagrams.get("module-graph", (None, ""))[1]
        combined.evidence["pre_built_dependency_graph"] = diagrams.get("class-hierarchy", (None, ""))[1]

        # ── 5. Synthesise wiki pages ─────────────────────────────────
        from close_wiki.synthesis.page_builder import CANONICAL_PAGES, PageBuilder  # noqa: PLC0415

        combined_for_build = _combine_results(merged_results)
        combined_for_build.evidence["pre_built_module_graph"] = combined.evidence["pre_built_module_graph"]
        combined_for_build.evidence["pre_built_dependency_graph"] = combined.evidence["pre_built_dependency_graph"]

        builder = PageBuilder(llm_config)
        pages: dict[str, tuple[str, str]] = {}

        page_bar = tqdm(
            CANONICAL_PAGES,
            desc="📝 Generating wiki pages",
            unit="page",
            dynamic_ncols=True,
            leave=True,
        )
        for slug in page_bar:
            page_bar.set_postfix(page=slug)
            _vlog(f"  Synthesising page: {slug}")
            try:
                page_result = builder.build_one(slug, combined_for_build)
                if page_result:
                    pages[slug] = page_result
                    _vlog(f"  → {slug}: {len(page_result[1])} chars")
            except Exception as exc:
                logger.error("Page %s failed: %s", slug, exc, exc_info=verbose)
                title = slug.replace("-", " ").title()
                pages[slug] = (title, f"# {title}\n\n> *Generation failed: {exc}*\n")

        page_bar.close()

        for slug, (title, content) in pages.items():
            store.upsert_page(run_id, slug, title, content)
        for name, (dtype, content) in diagrams.items():
            store.upsert_diagram(run_id, name, dtype, content)

        # ── 6. Export ────────────────────────────────────────────────
        _vlog("Exporting…")
        _log("Exporting…")
        from close_wiki.exporters.json_export import JsonExporter  # noqa: PLC0415
        from close_wiki.exporters.markdown_export import MarkdownExporter  # noqa: PLC0415

        MarkdownExporter(output_dir).export(pages, diagrams)
        JsonExporter(output_dir).export(run_id, files, combined, pages, diagrams)

        store.update_run_status(run_id, "success")
        _vlog("Done.")

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
