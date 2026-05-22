# rekipedia

**[English](README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md)**

> Your AI tech lead — always available, always up to date.

rekipedia scans any repository into a portable SQLite knowledge store and gives every developer an LLM-powered tech lead they can ask anything.

No hallucinations — every answer is grounded in your actual codebase.

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
| `reki watch .` | Auto-index on file change (OS watcher) |
| `reki hook install` | Git post-commit auto-rebuild |
| `reki mcp` | MCP stdio server for AI coding assistants |

---

## LLM configuration

After `reki init`, edit `.rekipedia/config.yml`:

```yaml
llm:
  model: ollama/llama4        # any litellm model string
  api_key: ""                 # or REKIPEDIA_API_KEY env var
  base_url: ""                # for local / self-hosted endpoints
  temperature: 0.2
```

Supported providers: Ollama, OpenAI, Anthropic, Gemini, any OpenAI-compatible endpoint.

Key env vars: `REKIPEDIA_MODEL`, `REKIPEDIA_API_KEY`, `REKIPEDIA_BASE_URL`

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

Proprietary and Confidential — Copyright © 2026 Eddie Chan. All Rights Reserved.
