# rekipedia

> Agentic repo-to-wiki: scan any repository into a portable SQLite knowledge store with wiki pages, diagrams, and grounded Q&A.

## Installation

### Homebrew (macOS / Linux)

```bash
brew tap unrealandychan/tap
brew install rekipedia
```

### Download Binary

Download the latest release from [GitHub Releases](https://github.com/unrealandychan/rekipedia/releases).

| Platform | Architecture | File |
|----------|-------------|------|
| macOS    | Apple Silicon (M1/M2/M3) | `rekipedia_darwin_arm64.tar.gz` |
| macOS    | Intel | `rekipedia_darwin_amd64.tar.gz` |
| Linux    | x86_64 | `rekipedia_linux_amd64.tar.gz` |
| Linux    | ARM64 | `rekipedia_linux_arm64.tar.gz` |
| Windows  | x86_64 | `rekipedia_windows_amd64.zip` |

Extract and move the binary to your `$PATH`:

```bash
tar -xzf rekipedia_darwin_arm64.tar.gz
mv rekipedia /usr/local/bin/
```

## Usage

```bash
# Scan a repository and generate wiki
rekipedia scan --path /path/to/repo

# Serve the wiki locally
rekipedia serve --path /path/to/repo

# Ask questions about the codebase
rekipedia ask --path /path/to/repo "How does the authentication work?"

# Update wiki after code changes
rekipedia update --path /path/to/repo

# Scan specific languages only
rekipedia scan --path /path/to/repo --languages go,python,typescript
```

## Commands

| Command | Description |
|---------|-------------|
| `scan` | Scan repository and generate wiki pages |
| `serve` | Start local web server to browse the wiki |
| `ask` | Ask questions about the codebase (grounded Q&A) |
| `update` | Incrementally update wiki after code changes |
| `embed` | Generate embeddings for semantic search |

## Supported Languages

- Go
- Python
- TypeScript / JavaScript
- Rust
- Java
- Ruby
- C / C++

## Configuration

Create a `config.yml` in your project root:

```yaml
llm:
  provider: openai
  model: gpt-4o
  api_key: your-api-key

output_dir: .wiki
```

## Full Documentation

See the [main repository](https://github.com/unrealandychan/rekipedia) for full documentation, Python package, and advanced usage.

---

## Go Port Charter

### What is the Go port?

This directory (`go/`) contains a **parallel implementation** of the full rekipedia pipeline written in Go. It replicates the core functionality — scanning, extracting symbols, synthesising wiki pages, embedding, RAG search, and serving — as a single self-contained binary with no Python runtime dependency.

### Is it a drop-in replacement for the Python implementation?

**No.** The Go port is an **experimental, high-performance alternative**, not a drop-in replacement. The canonical, primary implementation of rekipedia remains the Python package located at `src/rekipedia/`. The Go binary exposes a compatible CLI surface but internal behaviour, configuration keys, and edge-case handling may differ.

### Which implementation is canonical for production use?

**Python** (`src/rekipedia/`) is the canonical production implementation. It is the reference for correctness, receives features first, and is the version covered by the project's stability guarantees.

The Go port is suitable for users who:
- Cannot install a Python runtime in their environment.
- Need lower latency or reduced memory footprint for very large repositories.
- Are evaluating the port for potential wider adoption.

### Is feature parity required?

**Not currently.** The Go port tracks Python features on a **best-effort basis**. New features land in Python first; the Go port may lag behind or omit features that are difficult to express idiomatically in Go. Known gaps are tracked in [docs/plans/golang-rewrite.md](../docs/plans/golang-rewrite.md).

### Long-term direction

The long-term role of the Go port is **an open question**. Possible futures include:

- Promoting Go to co-primary status once feature parity is reached.
- Keeping Go as a lightweight "read-only" binary (serve + ask only) while Python owns write operations.
- Deprecating the Go port if maintenance overhead outweighs benefits.

No decision has been made. The current state is honestly: the Go port exists, it works for the majority of use cases, and its future will be decided collaboratively based on community feedback and contributor capacity. See ADR `docs/adr/0001-go-port-charter.md` for the formal record of this decision.
