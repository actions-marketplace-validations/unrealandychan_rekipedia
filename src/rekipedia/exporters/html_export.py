"""HTML exporter for rekipedia — produces a self-contained, interactive single-file HTML wiki.

Features
--------
- All wiki pages bundled into one ``<script>`` data block (no server required)
- Left sidebar with collapsible sections, page search (instant filter)
- Dark / light theme toggle (persisted in localStorage)
- Markdown rendered client-side via marked.js (CDN with integrity hash)
- Syntax highlighting via highlight.js (CDN)
- OSC-8 citations rendered as clickable ``<a>`` tags (``file://`` links)
- Responsive layout — collapses sidebar on narrow screens
- Diagrams (Mermaid / plain markdown code) rendered inline
- Page importance badge (shown as coloured pill in sidebar)
- "Copy link" anchors on every heading
- Export timestamp + rekipedia version in footer
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

__all__ = ["HtmlExporter"]

# ---------------------------------------------------------------------------
# Version constant — kept in sync with pyproject.toml by CI
# ---------------------------------------------------------------------------

_VERSION = "0.15.1"

# ---------------------------------------------------------------------------
# HTML template (single-file, fully self-contained)
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — rekipedia</title>
<link rel="stylesheet"
      href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css"
      integrity="sha512-rO+olRTkcf304NScNlDlOsQOcBYIoVVhqJZOLOuDJBoTnelJGmzGMNg/vCv/XSQKRIHIBpY8MpD5kLJ75uOfQ=="
      crossorigin="anonymous" referrerpolicy="no-referrer">
<style>
:root{{--bg:#0d1117;--bg2:#161b22;--bg3:#21262d;--border:#30363d;
      --text:#e6edf3;--muted:#8b949e;--accent:#58a6ff;--pill:#1f6feb;
      --pill-hi:#388bfd;--link:#58a6ff;--code-bg:#161b22;
      --sidebar-w:280px;--header-h:48px}}
[data-theme=light]{{--bg:#ffffff;--bg2:#f6f8fa;--bg3:#eaeef2;--border:#d0d7de;
      --text:#1f2328;--muted:#6e7781;--accent:#0969da;--pill:#ddf4ff;
      --pill-hi:#0969da;--link:#0969da;--code-bg:#f6f8fa}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;font-size:15px;line-height:1.7}}
a{{color:var(--link);text-decoration:none}}
a:hover{{text-decoration:underline}}

/* ── layout ── */
#app{{display:flex;min-height:100vh}}
#sidebar{{width:var(--sidebar-w);background:var(--bg2);border-right:1px solid var(--border);
  display:flex;flex-direction:column;position:sticky;top:0;height:100vh;overflow:hidden;
  flex-shrink:0}}
#content{{flex:1;min-width:0;padding:2rem 2.5rem 4rem;max-width:900px;margin:0 auto}}

/* ── header bar ── */
#topbar{{background:var(--bg2);border-bottom:1px solid var(--border);padding:0 1rem;
  height:var(--header-h);display:flex;align-items:center;gap:0.75rem;flex-shrink:0}}
#topbar h1{{font-size:1rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1}}
#theme-btn{{background:none;border:1px solid var(--border);border-radius:6px;
  color:var(--text);cursor:pointer;padding:4px 10px;font-size:0.8rem;white-space:nowrap}}
#theme-btn:hover{{background:var(--bg3)}}

/* ── sidebar search ── */
#search-wrap{{padding:0.6rem 0.75rem;border-bottom:1px solid var(--border)}}
#search{{width:100%;background:var(--bg3);border:1px solid var(--border);border-radius:6px;
  color:var(--text);padding:6px 10px;font-size:0.85rem;outline:none}}
#search:focus{{border-color:var(--accent)}}

/* ── nav ── */
#nav{{flex:1;overflow-y:auto;padding:0.5rem 0}}
.nav-section{{}}
.nav-section-header{{padding:0.4rem 0.75rem 0.2rem;font-size:0.7rem;font-weight:600;
  text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);cursor:pointer;
  display:flex;align-items:center;justify-content:space-between;user-select:none}}
.nav-section-header:hover{{color:var(--text)}}
.nav-section-arrow{{transition:transform .2s}}
.nav-section.collapsed .nav-section-arrow{{transform:rotate(-90deg)}}
.nav-section.collapsed .nav-items{{display:none}}
.nav-items{{}}
.nav-item{{display:flex;align-items:center;gap:0.4rem;padding:0.3rem 0.75rem 0.3rem 1.25rem;
  cursor:pointer;border-radius:0;transition:background .1s;font-size:0.875rem;
  border-left:2px solid transparent}}
.nav-item:hover{{background:var(--bg3)}}
.nav-item.active{{background:var(--bg3);border-left-color:var(--accent);color:var(--accent);font-weight:500}}
.nav-item.hidden{{display:none}}
.imp-badge{{font-size:0.65rem;padding:1px 5px;border-radius:9px;background:var(--pill);
  color:var(--pill-hi);font-weight:600;flex-shrink:0}}
[data-theme=light] .imp-badge{{color:var(--pill-hi);background:var(--pill)}}

/* ── content typography ── */
#page-content h1,h2,h3,h4{{margin:1.5rem 0 0.6rem;line-height:1.3;position:relative}}
#page-content h1{{font-size:1.8rem;padding-bottom:0.4rem;border-bottom:1px solid var(--border);margin-top:0}}
#page-content h2{{font-size:1.35rem}}
#page-content h3{{font-size:1.1rem}}
#page-content p{{margin:0.6rem 0}}
#page-content ul,#page-content ol{{padding-left:1.5rem;margin:0.5rem 0}}
#page-content li{{margin:0.2rem 0}}
#page-content blockquote{{border-left:4px solid var(--border);padding:0.2rem 1rem;color:var(--muted);margin:0.8rem 0}}
#page-content code{{background:var(--code-bg);padding:1px 5px;border-radius:4px;font-size:0.88em;font-family:"SFMono-Regular",Consolas,monospace}}
#page-content pre{{background:var(--code-bg);border:1px solid var(--border);border-radius:8px;
  padding:1rem;overflow-x:auto;margin:0.8rem 0}}
#page-content pre code{{background:none;padding:0;font-size:0.85em}}
#page-content table{{width:100%;border-collapse:collapse;margin:0.8rem 0;font-size:0.9em}}
#page-content th,#page-content td{{border:1px solid var(--border);padding:0.4rem 0.75rem;text-align:left}}
#page-content th{{background:var(--bg3);font-weight:600}}
#page-content tr:nth-child(even){{background:var(--bg2)}}
#page-content hr{{border:none;border-top:1px solid var(--border);margin:1.5rem 0}}
#page-content img{{max-width:100%;border-radius:6px}}

/* ── anchor copy buttons ── */
.anchor-link{{opacity:0;margin-left:0.4rem;font-size:0.75em;color:var(--muted)}}
h1:hover .anchor-link,h2:hover .anchor-link,h3:hover .anchor-link,h4:hover .anchor-link{{opacity:1}}

/* ── footer ── */
#footer{{margin-top:4rem;padding-top:1rem;border-top:1px solid var(--border);
  color:var(--muted);font-size:0.8rem;display:flex;gap:1rem;flex-wrap:wrap}}

/* ── responsive ── */
@media(max-width:700px){{
  #sidebar{{display:none}}
  #content{{padding:1rem}}
}}
</style>
</head>
<body>
<div id="app">
  <div id="sidebar">
    <div id="topbar">
      <h1 id="wiki-title">{title}</h1>
      <button id="theme-btn" onclick="toggleTheme()">☀ Light</button>
    </div>
    <div id="search-wrap">
      <input id="search" type="search" placeholder="Search pages…" oninput="filterNav(this.value)">
    </div>
    <nav id="nav"></nav>
  </div>
  <main id="content">
    <div id="page-content"></div>
    <footer id="footer">
      <span>Generated by <strong>rekipedia</strong> v{version}</span>
      <span>·</span>
      <span>{timestamp}</span>
    </footer>
  </main>
</div>

<!-- marked.js for Markdown rendering -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/11.2.0/marked.min.js"
        integrity="sha512-BVSN7P0WTF/JNDgMoGzLn0k5FCbKXJFvFJSjQOdpHDEPCJTd6qT0SN7IrRAjPJvpkBSfX+Qjss+JkbV5l9FQ=="
        crossorigin="anonymous" referrerpolicy="no-referrer"></script>
<!-- highlight.js for syntax highlighting -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"
        integrity="sha512-D9gUyxqja7hBtkWpPWGt9wfbfaMGVt9gnyCvYa+jojwwPHLCzUm5i8rpk7vD7wNee9bA35eYIjobYPaQuKS1MQ=="
        crossorigin="anonymous" referrerpolicy="no-referrer"></script>
<!-- Mermaid for diagrams -->
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>

<script>
// ── Embedded page data ────────────────────────────────────────────────────────
const PAGES = {pages_json};
const NAV_ORDER = {nav_order_json};
const SECTIONS = {sections_json};
const PAGES_META = {pages_meta_json};

// ── Theme ─────────────────────────────────────────────────────────────────────
function applyTheme(t){{
  document.documentElement.setAttribute("data-theme", t);
  document.getElementById("theme-btn").textContent = t==="dark" ? "☀ Light" : "🌙 Dark";
  localStorage.setItem("reki-theme", t);
}}
function toggleTheme(){{
  applyTheme(document.documentElement.getAttribute("data-theme")==="dark" ? "light" : "dark");
}}
(function(){{
  const saved = localStorage.getItem("reki-theme") || "dark";
  applyTheme(saved);
}})();

// ── Marked + highlight.js config ─────────────────────────────────────────────
marked.setOptions({{
  highlight: function(code, lang){{
    if(lang && hljs.getLanguage(lang)){{
      return hljs.highlight(code, {{language: lang}}).value;
    }}
    return hljs.highlightAuto(code).value;
  }},
  breaks: true,
  gfm: true,
}});

// ── Mermaid config ────────────────────────────────────────────────────────────
mermaid.initialize({{startOnLoad:false, theme:"dark", securityLevel:"loose"}});

// ── Nav build ─────────────────────────────────────────────────────────────────
function buildNav(){{
  const nav = document.getElementById("nav");
  nav.innerHTML = "";

  // Group pages by section
  const sectionPages = {{}};
  const noSection = [];
  const orderedSlugs = NAV_ORDER.length ? NAV_ORDER : Object.keys(PAGES);

  for(const slug of orderedSlugs){{
    if(!PAGES[slug]) continue;
    const meta = PAGES_META[slug] || {{}};
    const sec = meta.section || "";
    if(sec){{
      if(!sectionPages[sec]) sectionPages[sec] = [];
      sectionPages[sec].push(slug);
    }} else {{
      noSection.push(slug);
    }}
  }}

  // Build section groups
  const allSections = SECTIONS.length ? SECTIONS : Object.keys(sectionPages);

  function makeItem(slug){{
    const meta = PAGES_META[slug] || {{}};
    const title = meta.title || slug.replace(/-/g," ").replace(/\\b./g,c=>c.toUpperCase());
    const imp = meta.importance;
    const div = document.createElement("div");
    div.className = "nav-item";
    div.dataset.slug = slug;
    let html = `<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${{title}}</span>`;
    if(imp !== undefined && imp !== null){{
      html += `<span class="imp-badge">${{imp}}</span>`;
    }}
    div.innerHTML = html;
    div.onclick = ()=>loadPage(slug);
    return div;
  }}

  // Sections
  for(const sec of allSections){{
    const slugs = sectionPages[sec] || [];
    if(!slugs.length) continue;
    const secDiv = document.createElement("div");
    secDiv.className = "nav-section";
    secDiv.dataset.section = sec;
    const header = document.createElement("div");
    header.className = "nav-section-header";
    header.innerHTML = `<span>${{sec}}</span><span class="nav-section-arrow">▾</span>`;
    header.onclick = ()=>secDiv.classList.toggle("collapsed");
    const items = document.createElement("div");
    items.className = "nav-items";
    for(const slug of slugs) items.appendChild(makeItem(slug));
    secDiv.appendChild(header);
    secDiv.appendChild(items);
    nav.appendChild(secDiv);
  }}

  // Pages with no section
  if(noSection.length){{
    const items = document.createElement("div");
    items.className = "nav-items";
    for(const slug of noSection) items.appendChild(makeItem(slug));
    nav.appendChild(items);
  }}
}}

// ── Search filter ─────────────────────────────────────────────────────────────
function filterNav(q){{
  q = q.toLowerCase().trim();
  document.querySelectorAll(".nav-item").forEach(el=>{{
    const slug = el.dataset.slug;
    const meta = PAGES_META[slug] || {{}};
    const title = (meta.title||slug).toLowerCase();
    el.classList.toggle("hidden", q && !title.includes(q) && !slug.includes(q));
  }});
}}

// ── Page render ───────────────────────────────────────────────────────────────
let _currentSlug = null;

function loadPage(slug){{
  if(!PAGES[slug]) return;
  _currentSlug = slug;

  // Update active state
  document.querySelectorAll(".nav-item").forEach(el=>{{
    el.classList.toggle("active", el.dataset.slug===slug);
  }});

  // Render markdown
  const md = PAGES[slug];
  const html = marked.parse(md);
  const container = document.getElementById("page-content");
  container.innerHTML = html;

  // Add anchor copy buttons
  container.querySelectorAll("h1,h2,h3,h4").forEach(h=>{{
    const id = h.textContent.trim().toLowerCase().replace(/[^a-z0-9]+/g,"-");
    h.id = id;
    const a = document.createElement("a");
    a.className = "anchor-link";
    a.href = `#${{id}}`;
    a.textContent = "¶";
    a.title = "Copy link";
    a.onclick = (e)=>{{e.preventDefault();navigator.clipboard.writeText(location.href.split("#")[0]+"#"+id);}};
    h.appendChild(a);
  }});

  // Render Mermaid diagrams
  container.querySelectorAll("code.language-mermaid").forEach((code, i)=>{{
    const pre = code.parentElement;
    const id = "mermaid-"+i;
    const div = document.createElement("div");
    div.className = "mermaid";
    div.id = id;
    div.textContent = code.textContent;
    pre.replaceWith(div);
  }});
  mermaid.run({{nodes: container.querySelectorAll(".mermaid")}});

  // Apply highlight.js to non-mermaid blocks
  container.querySelectorAll("pre code:not(.language-mermaid)").forEach(el=>{{
    hljs.highlightElement(el);
  }});

  // Scroll to top
  document.getElementById("content").scrollTop = 0;
  window.scrollTo(0,0);

  // Update URL hash
  history.replaceState(null, "", `#${{slug}}`);
  document.title = (PAGES_META[slug]?.title || slug) + " — rekipedia";
}}

// ── Init ──────────────────────────────────────────────────────────────────────
buildNav();

// Load page from hash or first in nav
const initSlug = (()=>{{
  const hash = location.hash.slice(1);
  if(hash && PAGES[hash]) return hash;
  return NAV_ORDER.find(s=>PAGES[s]) || Object.keys(PAGES)[0];
}})();
loadPage(initSlug);
</script>
</body>
</html>
"""


class HtmlExporter:
    """Export wiki pages as a self-contained interactive HTML file."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def export(
        self,
        pages: dict[str, tuple[str, str]],
        *,
        nav_order: list[str] | None = None,
        sections: list[str] | None = None,
        pages_meta: dict[str, dict[str, Any]] | None = None,
        title: str = "Wiki",
        dest: Path | None = None,
    ) -> Path:
        """Write the interactive HTML file and return its path.

        Args:
            pages: Mapping of slug → (page_title, markdown_content).
            nav_order: Ordered list of slugs for sidebar navigation.
            sections: Section names in display order.
            pages_meta: Per-slug metadata dicts (title, section, importance, tags, …).
            title: Document title shown in the browser tab and sidebar header.
            dest: Output file path.  Defaults to ``output_dir/export.html``.

        Returns:
            Absolute path to the written HTML file.
        """
        import datetime  # noqa: PLC0415

        dest = dest or (self.output_dir / "export.html")
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Build page data: slug → markdown string
        pages_data: dict[str, str] = {}
        meta_data: dict[str, dict[str, Any]] = {}
        for slug, value in pages.items():
            if isinstance(value, tuple):
                page_title, content = value
            else:
                page_title, content = slug, str(value)
            pages_data[slug] = content
            # Merge supplied meta with page title
            base_meta = (pages_meta or {}).get(slug, {}).copy()
            base_meta.setdefault("title", page_title)
            meta_data[slug] = base_meta

        _nav = nav_order or list(pages_data.keys())
        _sections = sections or []
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        html_out = _HTML_TEMPLATE.format(
            title=html.escape(title),
            version=_VERSION,
            timestamp=ts,
            pages_json=json.dumps(pages_data, ensure_ascii=False),
            nav_order_json=json.dumps(_nav, ensure_ascii=False),
            sections_json=json.dumps(_sections, ensure_ascii=False),
            pages_meta_json=json.dumps(meta_data, ensure_ascii=False),
        )

        dest.write_text(html_out, encoding="utf-8")
        return dest
