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
        for slug in ordered_slugs:
            raw = available[slug].read_text(encoding="utf-8")
            title = slug.replace("-", " ").title()
            section = "general"
            # Parse frontmatter for title + section
            if raw.startswith("---"):
                end = raw.find("\n---", 3)
                if end != -1:
                    fm_text = raw[3:end]
                    for line in fm_text.splitlines():
                        if line.startswith("title:"):
                            t = line.split(":", 1)[1].strip().strip('"').strip("'")
                            if t:
                                title = t
                        elif line.startswith("section:"):
                            s = line.split(":", 1)[1].strip()
                            if s:
                                section = s
            # Fallback: extract H1 title
            if title == slug.replace("-", " ").title():
                for line in raw.splitlines():
                    line = line.strip()
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break
            pages.append({"slug": slug, "title": title, "section": section})
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
                lines = raw.splitlines()
                content_lines = lines

                # Strip YAML frontmatter only when it is a complete block at the
                # start of the document. A later '---' can be a normal Markdown
                # horizontal rule and must not cause the rest of the content to
                # be skipped.
                first_content_index = next(
                    (i for i, line in enumerate(lines) if line.strip()),
                    None,
                )
                if first_content_index is not None and lines[first_content_index].strip() == "---":
                    closing_index = next(
                        (
                            i
                            for i in range(first_content_index + 1, len(lines))
                            if lines[i].strip() == "---"
                        ),
                        None,
                    )
                    if closing_index is not None:
                        content_lines = lines[:first_content_index] + lines[closing_index + 1 :]

                snippet = []
                for line in content_lines:
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


    def _strip_yaml_frontmatter(text: str) -> str:
        """Strip a leading YAML frontmatter block delimited by exact `---` lines.

        If the closing delimiter is missing (malformed frontmatter) we still
        strip everything up to the first blank line or H1 heading so garbage
        YAML never leaks into the rendered page.
        """
        lines = text.splitlines(keepends=True)
        if not lines or lines[0] not in ("---\n", "---\r\n", "---"):
            return text

        # Normal case: find closing ---
        for idx in range(1, len(lines)):
            if lines[idx] in ("---\n", "---\r\n", "---"):
                return "".join(lines[idx + 1:]).lstrip("\r\n")

        # Malformed: no closing ---. Strip until first blank line or # heading.
        for idx in range(1, len(lines)):
            stripped = lines[idx].strip()
            if stripped == "" or stripped.startswith("#"):
                return "".join(lines[idx:]).lstrip("\r\n")

        # Everything looks like frontmatter: return empty rather than raw YAML.
        return ""

    def _render_md(path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        # Strip YAML frontmatter (--- ... ---) before rendering.
        # If the closing delimiter is missing the content is malformed; skip
        # stripping entirely so nothing is lost.
        text = _strip_yaml_frontmatter(text)
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

                # Load conversation history for multi-turn context
                db_path = output_dir / "store.db"
                chat_history: list[dict] = []
                if db_path.exists():
                    with SqliteStore(db_path) as _hs:
                        raw_hist = _hs.get_qa_history(str(repo_root), limit=20)
                    # get_qa_history returns newest-first; LLM needs oldest-first
                    for _h in reversed(raw_hist):
                        chat_history.append({"role": "user", "content": _h["question"]})
                        chat_history.append({"role": "assistant", "content": _h["answer"]})

                gen = stream_ask(
                    question=question,
                    repo_root=repo_root,
                    output_dir=output_dir,
                    llm_config=llm_config,
                    history=chat_history,
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
        """Return file-level module dependency graph as {nodes, edges}.

        Industry-standard approach (pydeps / pyreverse style):
        - Node  = source file (e.g. src/client.py)
        - Edge  = import relationship between files
        - kind  = 'module' for all file nodes
        Relationships table stores (from_=module_path, to=module_path, kind, file=source_file).
        We build a file→file import graph using the `file` column (source) and `to` column
        (target module, normalised to a file path that exists in our node set).
        """
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

            # ── Build file→kind map from symbols ─────────────────────────
            # Each file gets the "dominant" kind (class > function > module)
            KIND_RANK = {"class": 3, "function": 2, "method": 1, "module": 0}
            file_kind: dict[str, str] = {}
            file_package: dict[str, str] = {}
            for row in raw_symbols:
                kind = (row[2] if isinstance(row, (list, tuple)) else row.get("kind")) or "module"
                file_ = (row[3] if isinstance(row, (list, tuple)) else row.get("file")) or ""
                if not file_:
                    continue
                cur = file_kind.get(file_, "module")
                if KIND_RANK.get(kind, 0) > KIND_RANK.get(cur, 0):
                    file_kind[file_] = kind
                # package = first path segment (e.g. src/client.py → src)
                parts = file_.replace("\\", "/").split("/")
                file_package[file_] = parts[0] if len(parts) > 1 else "root"

            # Also collect files directly from relationships
            for row in raw_rels:
                file_ = (row[4] if isinstance(row, (list, tuple)) else row.get("file")) or ""
                if file_ and file_ not in file_kind:
                    file_kind[file_] = "module"
                    parts = file_.replace("\\", "/").split("/")
                    file_package[file_] = parts[0] if len(parts) > 1 else "root"

            god_set = {name for name, _ in god_nodes}

            nodes: list[dict] = []
            for file_, kind in sorted(file_kind.items()):
                label = file_.replace("\\", "/").split("/")[-1]  # basename
                nodes.append({
                    "id": file_,
                    "label": label,
                    "kind": kind,
                    "file": file_,
                    "group": file_package.get(file_, "root"),
                    "god": file_ in god_set or label in god_set,
                })

            node_ids = {n["id"] for n in nodes}

            # ── Build file→file edges from relationships ──────────────────
            # Strategy (pydeps-style):
            # The `file` column = the source file that contains the import.
            # The `to` column = dotted module name being imported.
            # We normalise `to` → candidate file paths and match against node_ids.
            def module_to_candidates(module: str) -> list[str]:
                """Convert dotted module name to candidate file paths."""
                # e.g. "src.client" → ["src/client.py", "src/client/__init__.py"]
                path_base = module.replace(".", "/")
                return [
                    f"{path_base}.py",
                    f"{path_base}/__init__.py",
                    # also try just the last segment in case it's a relative ref
                    f"{module.split('.')[-1]}.py",
                ]

            seen_edges: set[tuple[str, str]] = set()
            edges: list[dict] = []
            MAX_EDGES = 1500

            for row in raw_rels:
                src_file = (row[4] if isinstance(row, (list, tuple)) else row.get("file")) or ""
                to_module = (row[2] if isinstance(row, (list, tuple)) else row.get("to")) or ""
                kind_str = (row[3] if isinstance(row, (list, tuple)) else row.get("kind")) or "imports"

                if not src_file or not to_module:
                    continue
                if src_file not in node_ids:
                    continue

                # Try to resolve target module → file path
                tgt_file = None
                for cand in module_to_candidates(to_module):
                    if cand in node_ids:
                        tgt_file = cand
                        break

                if not tgt_file or tgt_file == src_file:
                    continue

                edge_key = (src_file, tgt_file)
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)
                edges.append({"source": src_file, "target": tgt_file, "kind": kind_str})
                if len(edges) >= MAX_EDGES:
                    break

            god_nodes_data = [{"name": name, "degree": degree} for name, degree in god_nodes]
            return JSONResponse({
                "nodes": nodes,
                "edges": edges,
                "god_nodes": god_nodes_data,
                "edge_count_total": len(edges),
            })
        except Exception as exc:
            return JSONResponse({"nodes": [], "edges": [], "god_nodes": [], "error": str(exc)})

    @app.get("/api/wiki/search", response_class=JSONResponse)
    async def wiki_search(q: str = ""):
        """Full-text search across wiki page titles and content."""
        q = q.strip().lower()
        if not q or len(q) < 2:
            return JSONResponse([])
        wiki_dir = output_dir / "wiki"
        if not wiki_dir.exists():
            return JSONResponse([])
        results = []
        for md_file in sorted(wiki_dir.glob("*.md")):
            raw = md_file.read_text(encoding="utf-8")
            slug = md_file.stem
            title = slug.replace("-", " ").title()
            section = "general"
            # Parse frontmatter
            body = raw
            if raw.startswith("---"):
                end = raw.find("\n---", 3)
                if end != -1:
                    fm_text = raw[3:end]
                    body = raw[end + 4:].lstrip()
                    for line in fm_text.splitlines():
                        if line.startswith("title:"):
                            t = line.split(":", 1)[1].strip().strip('"').strip("'")
                            if t:
                                title = t
                        elif line.startswith("section:"):
                            s = line.split(":", 1)[1].strip()
                            if s:
                                section = s
            # Plain-text body (strip markdown symbols)
            text_body = re.sub(r"[#*`\[\]()>_~]", " ", body)
            title_match = q in title.lower()
            section_match = q in section.lower()
            body_match = q in text_body.lower()
            if not (title_match or section_match or body_match):
                continue
            # Build snippet: find first matching line in body
            snippet = ""
            for line in text_body.splitlines():
                if q in line.lower() and line.strip():
                    snippet = line.strip()[:120]
                    break
            if not snippet and (title_match or section_match):
                # Just use first non-empty body line
                for line in text_body.splitlines():
                    if line.strip():
                        snippet = line.strip()[:120]
                        break
            results.append({
                "slug": slug,
                "title": title,
                "section": section,
                "snippet": snippet,
                "title_match": title_match,
            })
            if len(results) >= 20:
                break
        # Sort: title/section matches first
        results.sort(key=lambda r: (0 if r["title_match"] else 1, r["title"]))
        return JSONResponse(results)

    @app.get("/graph", response_class=HTMLResponse)
    async def graph_page(request: Request):
        pages = _wiki_pages()
        return templates.TemplateResponse(
            request, "graph.html",
            _ctx(request, pages=pages, project_name=_project_name()),
        )

    @app.get("/api/graph-data")
    async def graph_data():
        """Return graph nodes + edges as JSON."""
        db_path = output_dir / "store.db"
        if not db_path.exists():
            return JSONResponse({"nodes": [], "edges": []})
        try:
            with SqliteStore(db_path) as store:
                run_id = store.get_latest_run_id(str(repo_root))
                if not run_id:
                    return JSONResponse({"nodes": [], "edges": []})
                symbols = store.get_all_symbols(run_id)
                raw_rels = store.get_all_relationships(run_id)

            SECTION_COLORS = {
                "cli": "#4CAF50", "server": "#2196F3", "models": "#FF9800",
                "storage": "#9C27B0", "synthesis": "#F44336", "analysis": "#00BCD4",
                "orchestrator": "#FF5722", "extractors": "#795548", "rag": "#607D8B",
                "sandbox": "#E91E63",
            }
            DEFAULT_COLOR = "#9E9E9E"

            nodes = []
            for s in symbols:
                name = s[1] if isinstance(s, (list, tuple)) else (s.name if hasattr(s, "name") else s.get("name", ""))
                file = s[3] if isinstance(s, (list, tuple)) else (s.file if hasattr(s, "file") else s.get("file", ""))
                kind = s[2] if isinstance(s, (list, tuple)) else (s.kind if hasattr(s, "kind") else s.get("kind", ""))
                section = ""
                if file:
                    parts = file.split("/")
                    for part in parts:
                        if part in SECTION_COLORS:
                            section = part
                            break
                nodes.append({
                    "id": name,
                    "label": name,
                    "file": file,
                    "kind": kind,
                    "section": section,
                    "color": SECTION_COLORS.get(section, DEFAULT_COLOR),
                })

            label_to_id = {n["label"]: n["id"] for n in nodes}
            id_set = {n["id"] for n in nodes}

            def resolve_id(name: str):
                if not name: return None
                if name in label_to_id: return label_to_id[name]
                if name in id_set: return name
                parts = name.split(".")
                if len(parts) > 1 and parts[-1] in label_to_id:
                    return label_to_id[parts[-1]]
                if "." in name:
                    method = name.split(".")[-1]
                    if method in label_to_id: return label_to_id[method]
                return None

            edges = []
            KIND_PRIORITY = ["inherits", "calls", "imports", "unknown"]
            MAX_EDGES = 2000
            bucketed: dict[str, list] = {k: [] for k in KIND_PRIORITY}

            for rel in raw_rels:
                frm = rel[1] if isinstance(rel, (list, tuple)) else (rel.get("from_", "") or rel.get("from", ""))
                to = rel[2] if isinstance(rel, (list, tuple)) else rel.get("to", "")
                kind = rel[3] if isinstance(rel, (list, tuple)) else (rel.get("kind", "unknown") or "unknown")
                kind = kind or "unknown"
                src_id = resolve_id(frm)
                tgt_id = resolve_id(to)
                if src_id and tgt_id and src_id != tgt_id:
                    bucket = kind if kind in bucketed else "unknown"
                    bucketed[bucket].append({"source": src_id, "target": tgt_id, "kind": kind})

            for k in KIND_PRIORITY:
                edges.extend(bucketed[k])
                if len(edges) >= MAX_EDGES:
                    edges = edges[:MAX_EDGES]
                    break

            return JSONResponse({"nodes": nodes, "edges": edges})
        except Exception as exc:
            return JSONResponse({"nodes": [], "edges": [], "error": str(exc)})

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

    # ── Notes API ────────────────────────────────────────────────────

    @app.get("/api/notes", response_class=JSONResponse)
    async def api_notes_list():
        db_path = output_dir / "store.db"
        with SqliteStore(db_path) as store:
            return JSONResponse(store.list_notes())

    @app.post("/api/notes", response_class=JSONResponse)
    async def api_notes_create(request: Request):
        body = await request.json()
        content = body.get("content", "").strip()
        if not content:
            return JSONResponse({"error": "content required"}, status_code=400)
        tags = body.get("tags", "")
        if isinstance(tags, list):
            tags = ",".join(tags)
        db_path = output_dir / "store.db"
        with SqliteStore(db_path) as store:
            nid = store.upsert_note(content=content, tags=tags, source="manual")
            note = store.get_note(nid)
        return JSONResponse(note, status_code=201)

    @app.delete("/api/notes/{note_id}", response_class=JSONResponse)
    async def api_notes_delete(note_id: str):
        db_path = output_dir / "store.db"
        with SqliteStore(db_path) as store:
            deleted = store.delete_note(note_id)
        if deleted:
            return JSONResponse({"deleted": True})
        return JSONResponse({"error": "not found"}, status_code=404)

    @app.get("/notes", response_class=HTMLResponse)
    async def notes_page(request: Request):
        pages = _wiki_pages()
        db_path = output_dir / "store.db"
        with SqliteStore(db_path) as store:
            notes = store.list_notes()
        return templates.TemplateResponse(
            request, "notes.html",
            _ctx(request, pages=pages, notes=notes, project_name=_project_name()),
        )

    return app
