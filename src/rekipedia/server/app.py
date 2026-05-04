"""FastAPI web server for rekipedia serve."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated, AsyncIterator

import markdown as md
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from rekipedia.models.contracts import LLMConfig
from rekipedia.orchestrator.run_ask import run_ask, stream_ask
from rekipedia.storage.sqlite_store import SqliteStore

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_app(repo_root: Path, output_dir: Path, llm_config: LLMConfig) -> FastAPI:
    """Factory — returns a configured FastAPI app."""
    app = FastAPI(title="rekipedia", docs_url=None, redoc_url=None)

    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    # ── helpers ──────────────────────────────────────────────────────

    def _wiki_pages() -> list[dict]:
        wiki_dir = output_dir / "wiki"
        if not wiki_dir.exists():
            return []

        # Try to load nav_order from manifest.json (written by exporter)
        manifest_path = output_dir / "exports" / "manifest.json"
        nav_order: list[str] = []
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                nav_order = manifest.get("nav_order", [])
            except Exception:
                nav_order = []

        # Collect all available slugs from disk
        available = {f.stem: f for f in wiki_dir.glob("*.md")}
        if not available:
            return []

        # Build ordered list: nav_order first, then alphabetical remainder
        ordered_slugs: list[str] = []
        for slug in nav_order:
            if slug in available:
                ordered_slugs.append(slug)
        for slug in sorted(available):
            if slug not in ordered_slugs:
                ordered_slugs.append(slug)

        pages = []
        for i, slug in enumerate(ordered_slugs, start=1):
            # Extract H1 title from the markdown file for a nicer display name
            raw = available[slug].read_text(encoding="utf-8")
            title = slug.replace("-", " ").title()
            for line in raw.splitlines():
                line = line.strip()
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            pages.append({"slug": slug, "title": f"#{i} · {title}"})
        return pages

    def _project_name() -> str:
        """Extract project name from repo root directory name."""
        return repo_root.name.replace("-", " ").replace("_", " ").title()

    def _summary_html() -> str:
        """Read architecture-overview or index page for summary snippet."""
        wiki_dir = output_dir / "wiki"
        for slug in ("architecture-overview", "repository-structure", "getting-started"):
            p = wiki_dir / f"{slug}.md"
            if p.exists():
                raw = p.read_text(encoding="utf-8")
                # Take just the intro paragraph (before first ##)
                lines, snippet = raw.splitlines(), []
                in_frontmatter = False
                frontmatter_done = False
                for line in lines:
                    # Skip YAML frontmatter block (--- ... ---)
                    if not frontmatter_done and line.strip() == "---":
                        if not in_frontmatter:
                            in_frontmatter = True
                            continue
                        else:
                            in_frontmatter = False
                            frontmatter_done = True
                            continue
                    if in_frontmatter:
                        continue
                    if line.startswith("## ") and snippet:
                        break
                    if not line.startswith("# "):
                        snippet.append(line)
                text = "\n".join(snippet[:12]).strip()
                if text:
                    return md.markdown(text, extensions=["fenced_code", "tables"])
        return ""

    def _file_count() -> int:
        db_path = output_dir / "store.db"
        if not db_path.exists():
            return 0
        try:
            with SqliteStore(db_path) as store:
                run_id = store.get_latest_run_id(str(repo_root))
                if run_id:
                    files = store.get_files_for_run(run_id)
                    return len(files)
        except Exception:
            pass
        return 0


    def _render_md(path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        # Strip YAML frontmatter (--- ... ---) before rendering.
        # If the closing delimiter is missing the content is malformed; skip
        # stripping entirely so nothing is lost.
        if text.startswith("---\n") or text.startswith("---\r\n"):
            end = text.find("\n---", 3)
            if end != -1:
                text = text[end + 4:].lstrip("\n")
        return md.markdown(
            text,
            extensions=["fenced_code", "tables", "toc"],
        )

    def _ctx(request: Request, **kwargs) -> dict:
        """Build template context — always includes request for sidebar active-link logic."""
        return {"request": request, **kwargs}

    # ── routes ───────────────────────────────────────────────────────

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        pages = _wiki_pages()
        first_slug = pages[0]["slug"] if pages else None
        return templates.TemplateResponse(
            request, "index.html",
            _ctx(request, pages=pages, first_slug=first_slug,
                 project_name=_project_name(),
                 summary_html=_summary_html(),
                 file_count=_file_count()),
        )

    _SLUG_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

    @app.get("/wiki/{slug}", response_class=HTMLResponse)
    async def wiki_page(request: Request, slug: str):
        if not _SLUG_RE.match(slug):
            return HTMLResponse("<h1>Page not found</h1>", status_code=404)
        path = output_dir / "wiki" / f"{slug}.md"
        if not path.exists():
            return HTMLResponse("<h1>Page not found</h1>", status_code=404)
        html = _render_md(path)
        pages = _wiki_pages()
        return templates.TemplateResponse(
            request, "wiki.html",
            _ctx(request, pages=pages, slug=slug, content=html,
                 project_name=_project_name(),
                 title=slug.replace("-", " ").title()),
        )

    @app.get("/ask", response_class=HTMLResponse)
    async def ask_page(request: Request):
        db_path = output_dir / "store.db"
        history = []
        if db_path.exists():
            with SqliteStore(db_path) as store:
                history = store.get_qa_history(str(repo_root))
        pages = _wiki_pages()
        return templates.TemplateResponse(
            request, "ask.html",
            _ctx(request, pages=pages, history=history, project_name=_project_name()),
        )

    @app.get("/ask/stream", response_class=StreamingResponse)
    async def ask_stream(question: str, request: Request):
        """SSE endpoint — streams LLM tokens as Server-Sent Events."""
        async def _event_gen() -> AsyncIterator[str]:
            try:
                import asyncio  # noqa: PLC0415
                loop = asyncio.get_event_loop()
                # stream_ask is a sync generator; run in threadpool to avoid blocking
                import concurrent.futures  # noqa: PLC0415
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

                gen = stream_ask(
                    question=question,
                    repo_root=repo_root,
                    output_dir=output_dir,
                    llm_config=llm_config,
                )
                full_answer: list[str] = []
                for chunk in gen:
                    if await request.is_disconnected():
                        break
                    full_answer.append(chunk)
                    # Escape newlines so SSE data lines stay single-line
                    safe = chunk.replace("\n", "\\n")
                    yield f"data: {safe}\n\n"

                yield "data: [DONE]\n\n"

                # Persist full answer to history
                answer_text = "".join(full_answer)
                db_path = output_dir / "store.db"
                if db_path.exists() and answer_text:
                    with SqliteStore(db_path) as store:
                        store.save_qa(str(repo_root), question, answer_text, llm_config.model)
            except RuntimeError as exc:
                yield f"data: [ERROR] {exc}\n\n"
            except Exception as exc:
                yield f"data: [ERROR] {exc}\n\n"

        return StreamingResponse(
            _event_gen(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @app.post("/ask", response_class=JSONResponse)
    async def ask_submit(question: Annotated[str, Form()]):
        try:
            answer = run_ask(
                question=question,
                repo_root=repo_root,
                output_dir=output_dir,
                llm_config=llm_config,
            )
        except RuntimeError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)

        db_path = output_dir / "store.db"
        if db_path.exists():
            with SqliteStore(db_path) as store:
                store.save_qa(str(repo_root), question, answer, llm_config.model)

        return JSONResponse({"answer": answer})

    @app.get("/api/history", response_class=JSONResponse)
    async def api_history():
        db_path = output_dir / "store.db"
        if not db_path.exists():
            return JSONResponse([])
        with SqliteStore(db_path) as store:
            return JSONResponse(store.get_qa_history(str(repo_root)))

    @app.get("/api/graph", response_class=JSONResponse)
    async def api_graph():
        """Return dependency graph data as {nodes, edges}."""
        db_path = output_dir / "store.db"
        if not db_path.exists():
            return JSONResponse({"nodes": [], "edges": []})
        try:
            with SqliteStore(db_path) as store:
                run_id = store.get_latest_run_id(str(repo_root))
                if not run_id:
                    return JSONResponse({"nodes": [], "edges": []})
                raw_symbols = store.get_all_symbols(run_id)
                raw_rels = store.get_all_relationships(run_id)
                god_nodes = store.get_god_nodes(run_id, top_n=10)

            # raw_symbols rows: (run_id, name, kind, file, line_start, line_end, signature, docstring)
            seen_ids: set[str] = set()
            nodes: list[dict] = []
            for row in raw_symbols:
                name = row[1] if isinstance(row, (list, tuple)) else row["name"]
                kind = row[2] if isinstance(row, (list, tuple)) else row["kind"]
                file_ = row[3] if isinstance(row, (list, tuple)) else row["file"]
                node_id = f"{file_}::{name}" if file_ else name
                if node_id not in seen_ids:
                    seen_ids.add(node_id)
                    nodes.append({"id": node_id, "label": name, "kind": kind or "unknown", "file": file_ or ""})

            # Build label → node_id lookup for fast multi-strategy resolution
            label_to_id: dict[str, str] = {}
            id_set: set[str] = set()
            for n in nodes:
                label_to_id[n["label"]] = n["id"]
                id_set.add(n["id"])

            def resolve_id(name: str) -> str | None:
                """Try multiple strategies to resolve a relationship name to a node ID."""
                if not name:
                    return None
                # 1. Exact label match
                if name in label_to_id:
                    return label_to_id[name]
                # 2. Already a valid node ID
                if name in id_set:
                    return name
                # 3. Dotted module name — try last segment (e.g. rekipedia.cli.scan -> scan)
                parts = name.split(".")
                if len(parts) > 1 and parts[-1] in label_to_id:
                    return label_to_id[parts[-1]]
                # 4. Class.method format — try method name
                if "." in name:
                    method = name.split(".")[-1]
                    if method in label_to_id:
                        return label_to_id[method]
                return None

            # raw_rels rows: (run_id, from_, to, kind, file)
            # Priority order for edge limit: inherits > calls > imports
            KIND_PRIORITY = {"inherits": 0, "calls": 1, "imports": 2}
            raw_edges_by_kind: dict[str, list[dict]] = {"inherits": [], "calls": [], "imports": [], "unknown": []}
            for row in raw_rels:
                from_ = row[1] if isinstance(row, (list, tuple)) else row["from_"]
                to_ = row[2] if isinstance(row, (list, tuple)) else row["to"]
                kind = row[3] if isinstance(row, (list, tuple)) else row["kind"]
                kind_str = kind or "unknown"
                src_id = resolve_id(from_)
                tgt_id = resolve_id(to_)
                if src_id and tgt_id and src_id != tgt_id:
                    bucket = kind_str if kind_str in raw_edges_by_kind else "unknown"
                    raw_edges_by_kind[bucket].append({"source": src_id, "target": tgt_id, "kind": kind_str})

            # Merge in priority order, cap at 2000
            MAX_EDGES = 2000
            edges: list[dict] = []
            edge_count_total = sum(len(v) for v in raw_edges_by_kind.values())
            for bucket in ["inherits", "calls", "imports", "unknown"]:
                remaining = MAX_EDGES - len(edges)
                if remaining <= 0:
                    break
                edges.extend(raw_edges_by_kind[bucket][:remaining])

            god_nodes_data = [{"name": name, "degree": degree} for name, degree in god_nodes]

            return JSONResponse({"nodes": nodes, "edges": edges, "god_nodes": god_nodes_data, "edge_count_total": edge_count_total})
        except Exception as exc:
            return JSONResponse({"nodes": [], "edges": [], "god_nodes": [], "error": str(exc)})

    @app.get("/graph", response_class=HTMLResponse)
    async def graph_page(request: Request):
        pages = _wiki_pages()
        return templates.TemplateResponse(
            request, "graph.html",
            _ctx(request, pages=pages, project_name=_project_name()),
        )

    @app.get("/api/health", response_class=JSONResponse)
    async def api_health():
        db_path = output_dir / "store.db"
        if not db_path.exists():
            return JSONResponse({"status": "ok", "db": "no_store"})
        try:
            with SqliteStore(db_path) as store:
                store.get_qa_history(str(repo_root))  # lightweight probe
            return JSONResponse({"status": "ok", "db": "ok"})
        except Exception as exc:
            return JSONResponse(
                {"status": "degraded", "db": f"error: {exc}"},
                status_code=503,
            )

    return app
