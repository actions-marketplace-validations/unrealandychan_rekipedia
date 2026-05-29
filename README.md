# rekipedia

**Turn any repo into an AI-ready knowledge base — wiki, RAG, and MCP server included.**

[![PyPI version](https://img.shields.io/pypi/v/rekipedia.svg)](https://pypi.org/project/rekipedia/) [![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/) [![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE) [![MCP](https://img.shields.io/badge/MCP-compatible-purple.svg)](https://modelcontextprotocol.io)

---

## Why rekipedia?

| Problem | rekipedia |
|---|---|
| "Where does the auth logic live?" | `reki ask "how does auth work?"` → `src/auth.py:42` |
| Onboarding new devs takes days | `reki onboard .` generates a guided walkthrough in seconds |
| AI agents hallucinate about your codebase | `reki mcp` gives agents a grounded knowledge base with citations |
| Refactor anxiety | `reki hotspots` surfaces hub nodes and bridge nodes before you touch anything |
| Wiki goes stale immediately | `reki watch .` auto-reindexes on every file save |

---

## ⚡ Quickstart

```bash
pip install rekipedia
# or: npx rekipedia
```

### With LLM (richer wiki + Q&A)

```bash
export REKIPEDIA_API_KEY=sk-...
reki scan .
reki ask "how does authentication work?"
```

---

## Key Features

### 🗂 `reki scan` — Instant knowledge store

Parses your repo into a SQLite knowledge store with symbols, relationships, and auto-generated wiki pages.

```bash
reki scan .            # full scan with LLM summaries
reki scan . --no-llm   # zero config, no API key required
```

### 💬 `reki ask` — Q&A grounded in your code

Answers questions with file:line citations. No hallucinations — every answer is backed by indexed source.

```bash
reki ask "what is the entry point?"
reki ask "which modules handle payments?" --brief
```

```
Answer: The entry point is src/main.py:12 — `App.run()` bootstraps the server.
Sources: src/main.py:12, src/server.py:34
```

### 🤖 `reki mcp` — MCP server for AI agents

Plug rekipedia directly into Claude Code, Cursor, or any MCP-aware agent.

```bash
reki mcp
```

Available tools: `ask`, `search_nodes`, `get_context`, `get_relationships`, `get_hub_nodes`, `get_impact`

### 🔥 `reki hotspots` — Architectural hotspot detection

Finds hub and bridge nodes — the files your whole codebase depends on.

```bash
reki hotspots
```

```
Hub nodes:   src/core/engine.py (42 dependents)
Bridge nodes: src/adapters/db.py (connects 3 clusters)
```

### 🔄 `reki update` — Incremental updates

Only regenerates wiki pages affected by your changes.

```bash
reki update . --impact-only
```

---

## MCP Integration

rekipedia ships a full MCP stdio server. Connect it to any MCP-aware agent in seconds.

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "rekipedia": {
      "command": "reki",
      "args": ["mcp"],
      "cwd": "."
    }
  }
}
```

Claude Code and Cursor will automatically discover this config. The agent can then call:

- `ask` — Q&A over the codebase
- `search_nodes` — symbol/file search
- `get_context` — file-level context
- `get_relationships` — dependency graph queries
- `get_hub_nodes` — architectural hotspots
- `get_impact` — change impact analysis

---

## LLM Setup

rekipedia works without an LLM (`--no-llm`). To enable richer summaries and Q&A:

```bash
export REKIPEDIA_API_KEY=sk-...          # OpenAI, Anthropic, or compatible
export REKIPEDIA_MODEL=gpt-4o           # default: gpt-4o
```

Any OpenAI-compatible endpoint works:

```bash
export REKIPEDIA_API_KEY=ollama
export REKIPEDIA_MODEL=ollama/llama3
```

---

## Commands

| Command | Description |
|---|---|
| `reki scan .` | Full scan — index symbols, generate wiki |
| `reki scan . --no-llm` | Scan without LLM, zero config |
| `reki ask "question"` | Ask anything about the codebase |
| `reki ask "question" --brief` | Short answer mode |
| `reki update . --impact-only` | Incremental update, affected pages only |
| `reki serve .` | Local web UI at `http://127.0.0.1:7070` |
| `reki embed .` | Build FAISS semantic index |
| `reki publish . [--output-dir PATH]` | Publish wiki to a git-tracked directory for team sharing |
| `reki export . --format bundle` | Export a content-addressed wiki bundle for team sync |
| `reki merge <bundle-A> <bundle-B> [--base BASE]` | Three-way wiki merge — conflict-free team sync |
| `reki pull [URL]` | Fetch and merge a remote wiki bundle (HTTPS/S3/GCS) |
| `reki watch . --publish` | Auto-index + auto-publish wiki on every file save |
| `reki export . --format md\|zip\|json\|html\|bundle` | Export the wiki |
| `reki diff` | Show impact of uncommitted changes |
| `reki hotspots` | Hub & bridge node detection |
| `reki refactor . --dry-run` | Preview refactor suggestions |
| `reki refactor . --apply` | Apply refactor suggestions |
| `reki mcp` | Start MCP stdio server |
| `reki review` | LLM-powered PR review |
| `reki watch .` | Auto-index on file change |
| `reki hook install` | Install git post-commit hook |

---

## FAQ

### Q: Why is `store.db` gitignored? How do teammates use rekipedia?

`store.db` is a binary SQLite file containing machine-specific absolute paths — committing it would cause path mismatches on other machines and create noisy binary diffs. Each developer runs `reki scan .` locally to build their own store. To share the human-readable output with your team, use `reki publish .`, which copies the generated wiki pages to `docs/wiki/` so they can be committed and browsed in your repo or docs site.

---

### Q: What is `store.db` for vs the FAISS index? Why do I need both?

They serve distinct purposes and are not interchangeable. `store.db` is a structured SQLite graph: it stores symbols, relationships, file manifests, and scan run history — the kind of data you query with precise filters ("find all callers of function X"). The FAISS index (built by `reki embed .`) stores dense embedding vectors for every chunk of your codebase, enabling fuzzy semantic search ("find code that handles authentication"). `reki ask` uses both together: BM25 keyword search over SQLite and vector similarity search over FAISS, then merges the results.

---

### Q: Can I use Postgres, MySQL, or another database instead of SQLite?

Not currently. SQLite is the only supported backend for the structured symbol/relationship store, and it is intentional — SQLite is zero-config, portable, and requires no running server, which keeps `reki scan` self-contained. The `reki export .` command produces JSON exports (`symbols.json`, `relationships.json`) you can load into any database. Postgres/MySQL support is not on the roadmap, but the JSON exports make integration with your own tooling straightforward.

---

### Q: Does rekipedia support Qdrant or Chroma instead of FAISS?

Yes. FAISS is the default vector backend, but Qdrant and Chroma are both supported as optional backends. Qdrant and Chroma are useful when you want a persistent, server-hosted vector store shared across machines — unlike the local FAISS index, a running Qdrant or Chroma instance can be queried by your whole team without each person running `reki embed`. Install the relevant extras (`pip install rekipedia[qdrant]` or `rekipedia[chroma]`) and configure the backend in `.rekipedia/config.yml`.

---

### Q: Do I need an OpenAI API key?

No. rekipedia can run entirely without an LLM using the `--no-llm` flag — `reki scan . --no-llm` performs static analysis only, producing the symbol graph and wiki structure without AI-generated summaries. When you do want richer summaries and Q&A, rekipedia supports OpenAI, Anthropic, Ollama (local), Azure OpenAI, and any OpenAI-compatible endpoint. For fully offline usage, point it at a local [Ollama](https://ollama.com) instance — no internet required.

---

### Q: How do I share the wiki with my team without everyone running `reki scan`?

Use `reki publish .`. This command copies the generated `wiki/*.md` and `diagrams/*.md` files into `docs/wiki/` (not gitignored), which can be committed and browsed directly in GitHub, your docs site, or any Markdown viewer — no local scan required. The best setup is to automate publishing in CI so the wiki stays current whenever the main branch changes (see the GitHub Actions question below).

---

### Q: How do I keep the wiki up to date automatically?

Run `reki init --with-ci` to scaffold a GitHub Actions workflow (`.github/workflows/rekipedia-wiki.yml`) that runs `reki scan`, then `reki publish` on every push to `main`. The workflow commits any changes to `docs/wiki/` back to the repo automatically. Set `REKIPEDIA_API_KEY` as a repository secret for LLM-enriched pages; omit it and the workflow falls back to `--no-llm` mode at zero cost.

---

### Q: How does team sync work for distributed teams?

rekipedia's team sync is a multi-layer system for conflict-free wiki collaboration:

1. **Bundle** — `reki export --format bundle` creates a deterministic, content-addressed snapshot with a stable `bundle_id` and per-page hash trailers.
2. **Merge** — `reki merge bundle-A bundle-B --base bundle-base` performs a three-way merge: pages changed by only one developer are accepted automatically; only genuinely divergent pages produce conflict markers.
3. **Git merge driver** — `reki init --with-merge-driver` registers a git merge driver so `git merge` and `git pull` automatically use rekipedia's merge logic — no `<<<<<<` conflicts in generated wiki files.
4. **Live sync** — `reki watch . --publish` publishes the wiki after every incremental update, keeping `docs/wiki/` in sync as you code. Set `team.sync_dir` in `.rekipedia/config.yml` for the default target.
5. **Remote pull** — `reki pull <url>` fetches a bundle from HTTPS, S3, or GCS and merges it locally. Combine with `reki init --with-ci --with-upload s3` to have CI upload a fresh bundle after every main-branch push.

---

### Q: How does `reki ask` actually work under the hood?

`reki ask "question"` runs a hybrid retrieval pipeline. First, it executes a BM25 keyword search against the SQLite store to find exact and near-exact symbol/token matches. In parallel, it encodes your question into an embedding vector and queries the FAISS (or Qdrant/Chroma) index for semantically similar chunks. The two result sets are merged and re-ranked by relevance score, then the top chunks are passed as context to your configured LLM, which synthesises a final answer with file:line citations. With `--no-llm`, retrieval results are returned directly without synthesis.

---

### Q: How large does `store.db` / the FAISS index get on a large repo?

For a typical mid-size repo (50k–200k lines of code), `store.db` is usually 10–80 MB. The FAISS index in `.rekipedia/rag/` scales with the number of embedded chunks — expect 50–500 MB for the same size range, which is why `rag/` is gitignored by default. On very large monorepos (1M+ LOC), the FAISS index can exceed 1 GB; in that case, switching to a server-backed Qdrant instance is recommended so the index lives outside your working directory.

---

### Q: Can rekipedia scan private or fully offline repos?

Yes, fully. `reki scan` is pure static analysis — it never sends your source code anywhere. With `--no-llm`, the entire pipeline is offline and air-gap safe. When LLM features are enabled, only retrieved *chunks* (not your full source) are sent to the LLM provider as context; if you use Ollama, even that stays local. There are no telemetry calls, no license checks against a remote server, and no requirement for internet access beyond reaching your chosen LLM API endpoint.

---

## Coming Soon

- **Hosted wiki** — share your knowledge base with a link, no self-hosting required
- **VS Code extension** — inline `reki ask` from your editor

---

## Contributing

rekipedia is going MIT open source. Contributions welcome.

```bash
git clone https://github.com/unrealandychan/rekipedia.git
pip install -e ".[dev]"
```

Open an issue or PR — the bar is low and the maintainer is responsive.

---

**Current version:** `0.17.25` · [PyPI](https://pypi.org/project/rekipedia/) · [MIT License](LICENSE)
