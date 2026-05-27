# rekipedia

[![PyPI version](https://img.shields.io/pypi/v/rekipedia.svg)](https://pypi.org/project/rekipedia/) [![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/) [![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE) [![MCP](https://img.shields.io/badge/MCP-compatible-purple.svg)](https://modelcontextprotocol.io)

**[English](README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md)**

> Your AI tech lead — always available, always up to date.

rekipedia scans any repository into a portable SQLite knowledge store and gives every developer an LLM-powered tech lead they can ask anything.

No hallucinations — every answer is grounded in your actual codebase.

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

## Quick start

```bash
# No install required
npx rekipedia init . && npx rekipedia scan .
# or
uvx rekipedia init . && uvx rekipedia scan .
```

```bash
# Permanent install
pip install rekipedia          # core
pip install "rekipedia[rag]"   # + semantic search (FAISS)
```

---

## Core commands

| Command | What it does |
|---|---|
| `reki init .` | Scaffold config |
| `reki scan .` | Full analysis → wiki + knowledge store |
| `reki update .` | Incremental refresh (changed files only) |
| `reki update . --impact-only` | Impact-aware mode — only regenerates wiki pages for affected modules |
| `reki serve .` | Local web UI — browse, search, ask AI |
| `reki ask` | Interactive Q&A REPL (streamed) |
| `reki embed .` | Build FAISS semantic index for hybrid RAG |
| `reki export .` | Bundle wiki → `--format md\|zip\|json\|html` |
| `reki diff` | Uncommitted-change impact analysis |
| `reki domain .` | Map codebase to business layers (API/Service/Data/UI) |
| `reki tour .` | Guided learning walkthrough by dependency depth |
| `reki onboard .` | Static onboarding guide for new developers |
| `reki review` | LLM PR review grounded in wiki context |
| `reki refactor .` | Detect code smells → `REFACTOR.md` |
| `reki refactor . --dry-run` | Preview refactor suggestions without writing files |
| `reki refactor . --apply` | Auto-apply safe fixes (dead code markers, split suggestions) |
| `reki refactor . --apply --dry-run` | Preview what `--apply` would do |
| `reki watch .` | Auto-index on file change (OS watcher) |
| `reki hook install` | Git post-commit auto-rebuild |
| `reki mcp` | MCP stdio server for AI coding assistants |

---

### `reki ask` — Brief mode

```bash
# Brief mode — ~150 tokens, summary + citations only
reki ask "what does Scanner.scan() do?" --brief

# Or via env var (useful for piping)
REKIPEDIA_BRIEF=1 reki ask "entry point?" | grep 'src/'
```

---

## LLM Setup

rekipedia uses [litellm](https://github.com/BerriAI/litellm) and supports any provider:

| Provider | Example |
|---|---|
| OpenAI | `OPENAI_API_KEY=sk-... reki scan .` |
| Anthropic Claude | `REKIPEDIA_MODEL=claude-3-5-sonnet-20241022 REKIPEDIA_API_KEY=sk-ant-... reki scan .` |
| Google Gemini | `REKIPEDIA_MODEL=gemini/gemini-2.0-flash REKIPEDIA_API_KEY=AIza... reki scan .` |
| OpenRouter | `REKIPEDIA_MODEL=openrouter/anthropic/claude-3.5-sonnet REKIPEDIA_API_KEY=sk-or-... reki scan .` |
| Local Ollama (default) | `REKIPEDIA_MODEL=ollama/llama4 reki scan .` |
| Azure OpenAI | `REKIPEDIA_MODEL=azure/gpt-4o REKIPEDIA_BASE_URL=https://your-resource.openai.azure.com REKIPEDIA_API_KEY=... reki scan .` |

After `reki init`, edit `.rekipedia/config.yml`:

```yaml
llm:
  model: ollama/llama4        # any litellm model string
  api_key: ""                 # or REKIPEDIA_API_KEY env var
  base_url: ""                # for local / self-hosted endpoints
  temperature: 0.2
```

Supported providers: Ollama, OpenAI, Anthropic, Gemini, any OpenAI-compatible endpoint.

Environment variables:
- `REKIPEDIA_MODEL` — litellm model string (default: `ollama/llama4`)
- `REKIPEDIA_API_KEY` — API key for the chosen provider
- `REKIPEDIA_BASE_URL` — custom base URL (for Azure, Ollama, proxies)
- `REKIPEDIA_TIMEOUT` — LLM call timeout in seconds (default: 180)

---

## Output layout

```
.rekipedia/
├── config.yml          # settings (committed)
├── store.db            # SQLite knowledge store (git-ignored)
├── wiki/               # generated Markdown pages
├── rag/                # FAISS index + chunks (git-ignored)
├── diagrams/           # Mermaid diagrams
└── exports/            # JSON exports + manifest
```

---

## Python API

```python
import rekipedia

result = rekipedia.scan("/path/to/repo")
answer = rekipedia.ask("/path/to/repo", "How does the auth flow work?")
print(answer.text)
for c in answer.citations:
    print(f"  {c.file}:{c.line}")
```

Async variants: `rekipedia.scan_async()`, `rekipedia.ask_async()`

---

## Development

```bash
make dev      # install deps
make test     # run tests
make lint     # lint
make build    # wheel + npm tarball
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.
