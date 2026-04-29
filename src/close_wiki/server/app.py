"""FastAPI web server for close-wiki serve."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

import markdown as md
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from close_wiki.models.contracts import LLMConfig
from close_wiki.orchestrator.run_ask import run_ask
from close_wiki.storage.sqlite_store import SqliteStore

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_app(repo_root: Path, output_dir: Path, llm_config: LLMConfig) -> FastAPI:
    """Factory — returns a configured FastAPI app."""
    app = FastAPI(title="close-wiki", docs_url=None, redoc_url=None)

    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    # ── helpers ──────────────────────────────────────────────────────

    def _wiki_pages() -> list[dict]:
        wiki_dir = output_dir / "wiki"
        pages = []
        if wiki_dir.exists():
            for f in sorted(wiki_dir.glob("*.md")):
                pages.append({"slug": f.stem, "title": f.stem.replace("-", " ").title()})
        return pages

    def _render_md(path: Path) -> str:
        return md.markdown(
            path.read_text(encoding="utf-8"),
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
            _ctx(request, pages=pages, first_slug=first_slug),
        )

    @app.get("/wiki/{slug}", response_class=HTMLResponse)
    async def wiki_page(request: Request, slug: str):
        path = output_dir / "wiki" / f"{slug}.md"
        if not path.exists():
            return HTMLResponse("<h1>Page not found</h1>", status_code=404)
        html = _render_md(path)
        pages = _wiki_pages()
        return templates.TemplateResponse(
            request, "wiki.html",
            _ctx(request, pages=pages, slug=slug, content=html,
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
            _ctx(request, pages=pages, history=history),
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

    return app
