# close-wiki

> Your AI tech lead — always available, always up to date.

close-wiki scans any repository into a portable SQLite knowledge store and gives every developer on the team an LLM-powered tech lead they can ask anything: _"How does the auth flow work?", "What's the fastest way to add a new API endpoint?", "What broke the payment service last week?"_

No hallucinations, no guessing — every answer is grounded in your actual codebase.

## Quick start

### via npm / npx (no install required)

```bash
npx close-wiki init .
npx close-wiki scan .
```

### via uv / uvx (no install required)

```bash
uvx close-wiki init .
uvx close-wiki scan .
```

### Permanent install

```bash
# Python
uv tool install close-wiki
# or
pip install close-wiki

# Node (adds global `close-wiki` binary that delegates to Python)
npm install -g close-wiki
```

---

## Commands

| Command | Description |
|---|---|
| `close-wiki init [REPO]` | Scaffold `.close-wiki/` with `config.yml` and update `.gitignore` |
| `close-wiki scan [REPO]` | Full analysis — extracts symbols, synthesises wiki pages, exports JSON |
| `close-wiki update [REPO]` | Incremental refresh — re-extracts only changed files, keeps the rest |
| `close-wiki ask QUESTION` | Grounded Q&A: answers drawn exclusively from the wiki + symbol index |

---

## LLM configuration

After running `close-wiki init`, edit `.close-wiki/config.yml`:

```yaml
version: 1
ignore:
  - .git
  - node_modules
  - __pycache__
  - .close-wiki
languages:
  - python
  - typescript
llm:
  model: ollama/llama4        # any litellm model string
  api_key: ""                 # or set CLOSE_WIKI_API_KEY env var
  base_url: ""                # for local / self-hosted endpoints
  temperature: 0.2
```

### Supported providers (via [litellm](https://docs.litellm.ai))

| Provider | Example model string |
|---|---|
| Ollama (local, free) | `ollama/llama4` |
| OpenAI | `gpt-5.5` |
| Anthropic | `claude-opus-4-6` |
| Google Gemini | `gemini/gemini-3.0-pro` |
| Any OpenAI-compatible | set `base_url` in config |

### Runtime overrides (env vars)

```bash
export CLOSE_WIKI_MODEL=gpt-5.5
export CLOSE_WIKI_API_KEY=sk-...
export CLOSE_WIKI_BASE_URL=https://my-proxy/v1
```

---

## Output

`close-wiki scan` writes everything to `.close-wiki/` inside your repo:

```
.close-wiki/
├── config.yml              # your settings (committed)
├── store.db                # SQLite knowledge store (git-ignored)
├── wiki/                   # generated Markdown pages
│   ├── index.md
│   ├── architecture.md
│   ├── core-modules.md
│   ├── build-and-deploy.md
│   └── testing-strategy.md
├── diagrams/               # Mermaid diagram files
│   ├── module-graph.md
│   └── class-hierarchy.md
└── exports/                # JSON exports
    ├── symbols.json
    ├── relationships.json
    └── manifest.json       # run summary + metadata
```

### Scan options

```bash
# Use a specific LLM model
close-wiki scan . --model gpt-5.5

# Skip Docker (run extractors in-process)
close-wiki scan . --no-docker

# Write output to a custom directory
close-wiki scan . --output-dir /tmp/wiki-output
```

### Incremental update

After the first scan, `close-wiki update` only re-processes files whose SHA-256 has changed. Unchanged symbols and relationships are carried forward from the previous run — the wiki is refreshed in seconds.

```bash
close-wiki update .                    # auto-detect changed files
close-wiki update . --no-docker        # skip Docker
```

If no previous scan is found, `update` automatically falls back to a full scan.

### Ask the wiki

```bash
close-wiki ask "How does the auth flow work?"
close-wiki ask "What are the entry points?" --model gpt-5.5
close-wiki ask "How do I run the tests?" --repo ./my-project
```

Answers are grounded **entirely** in your wiki pages and symbol index — the LLM cannot hallucinate details that aren't in the scanned knowledge store.

Not happy with a generated page? See **[docs/customizing.md](docs/customizing.md)** — you can pin pages, override prompts, change the writing style, or add your own pages that scans will never touch.

---

## Prerequisites

- **Python ≥ 3.11** (or `uv` which manages its own Python)
- **Docker** — optional; used for isolated extraction. Falls back to in-process runner automatically if Docker is not available (`--no-docker` forces in-process mode)

---

## Development

```bash
# Install all deps
make dev

# Run tests
make test

# Lint
make lint

# Build wheel + npm tarball
make build
```

### Release

```bash
PYPI_TOKEN=pypi-... NPM_TOKEN=npm_... make release
```

---

## License

MIT — see [LICENSE](LICENSE).
