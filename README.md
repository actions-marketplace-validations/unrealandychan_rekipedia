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
| `reki export . --format md\|zip\|json\|html` | Export the wiki |
| `reki diff` | Show impact of uncommitted changes |
| `reki hotspots` | Hub & bridge node detection |
| `reki refactor . --dry-run` | Preview refactor suggestions |
| `reki refactor . --apply` | Apply refactor suggestions |
| `reki mcp` | Start MCP stdio server |
| `reki review` | LLM-powered PR review |
| `reki watch .` | Auto-index on file change |
| `reki hook install` | Install git post-commit hook |

---

## Coming Soon

- **Hosted wiki** — share your knowledge base with a link, no self-hosting required
- **Team sync** — collaborative wiki with conflict-free merge for distributed teams
- **GitHub Action** — auto-update wiki on every push
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
