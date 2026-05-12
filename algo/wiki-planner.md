# Wiki Planner — LLM-Driven Structure Planning

**Source:** `src/rekipedia/synthesis/planner.py`, `src/rekipedia/synthesis/agent_planner.py`
**Used by:** `reki scan` (wiki generation phase)

## Overview

After symbol extraction, rekipedia dynamically decides **which wiki pages to generate and how** — rather than using a hardcoded template. The planner takes the analysis result (symbols, relationships, file structure) and outputs a `WikiPlan`.

## Two Modes

| Mode | Source | Activation |
|---|---|---|
| **Single-shot** (default) | `planner.py` | Always available |
| **Agentic** | `agent_planner.py` | `REKIPEDIA_AGENT_PLANNER=1` |

## Mode 1 — Single-Shot JSON Planner

The LLM receives a planning summary (symbol counts, top files, language distribution) and outputs a **single JSON blob** defining all pages at once.

### Output Schema

```json
{
  "sections": [{"id": "...", "title": "...", "pages": [...]}],
  "pages": [{
    "slug": "lowercase-hyphenated",
    "title": "Human Readable Title",
    "section": "section-id",
    "priority": 1,
    "importance": 90,
    "focus": "Detailed instruction for page writer",
    "required_data": ["symbols", "relationships"],
    "tags": ["overview"],
    "keywords": ["AuthService", "jwt", "token"]
  }],
  "nav_order": ["index", "architecture-overview", ...],
  "index_slug": "index"
}
```

### `importance` field (0–100)

| Range | Pages |
|---|---|
| 95–100 | `index`, `architecture-overview` |
| 80–94 | Core module pages, data-flow |
| 60–79 | API reference, configuration, testing |
| 40–59 | Internals, algorithms, contributing |
| 20–39 | Ecosystem, deployment, integrations |

Drives nav prominence in web UI + determines read order for `reki ask` context loading.

### Always-Required Pages

- `index` — project overview, quick-start, repo tree
- `repository-structure` — if file_count ≥ 10
- `architecture-overview` — Mermaid diagram + component map
- `technical-debt` — **always included** (importance: 70), analyses TODO/FIXME, missing tests, code smells

## Mode 2 — Agentic Planner (tool-calling)

Instead of one JSON blob, the LLM builds the plan **incrementally** using tools:

| Tool | Effect |
|---|---|
| `add_section(id, title, pages)` | Register a navigation section |
| `add_page(slug, title, section, ...)` | Add one wiki page spec |
| `finalize(nav_order)` | Lock the plan — terminates loop |

**Max iterations:** 20 (hardcoded in `agent_planner.py`).

**Why agentic?** For large repos, the JSON output can exceed model limits. Tool-calling lets the model build incrementally and self-correct (e.g. re-add a page with better `focus`).

## `keywords` Field

Each page spec includes 5–10 exact symbol names or domain terms. Used for **fast retrieval** during `reki ask` — when a question mentions `"AuthService"`, the planner can instantly route to the `authentication` page without vector search.

## Page Generation (after planning)

Each page in the plan is rendered by `page_builder.py` using:
1. Relevant symbols (filtered by `keywords`)
2. Relationships graph subset
3. LLM call with `focus` as the instruction

Pages are generated in **parallel** (`ThreadPoolExecutor`, `_MAX_PAGE_WORKERS=4`).

## Trade-offs

| Aspect | Current | Alternative |
|---|---|---|
| Plan quality | Depends on LLM | Could use templates for small repos |
| `technical-debt` always included | Hardcoded in prompt | User-configurable `--exclude technical-debt` |
| Page count | Min 5, max 15 | Should scale with repo size |
| `importance` scoring | LLM-assigned | Could compute from symbol degree centrality |
