# close-wiki

> Agentic repo-to-wiki: scan any repository into a portable SQLite knowledge store with wiki pages, diagrams, and grounded Q&A.

## Installation

### Homebrew (macOS / Linux)

```bash
brew tap unrealandychan/tap
brew install close-wiki
```

### Download Binary

Download the latest release from [GitHub Releases](https://github.com/unrealandychan/close-wiki/releases).

| Platform | Architecture | File |
|----------|-------------|------|
| macOS    | Apple Silicon (M1/M2/M3) | `close-wiki_darwin_arm64.tar.gz` |
| macOS    | Intel | `close-wiki_darwin_amd64.tar.gz` |
| Linux    | x86_64 | `close-wiki_linux_amd64.tar.gz` |
| Linux    | ARM64 | `close-wiki_linux_arm64.tar.gz` |
| Windows  | x86_64 | `close-wiki_windows_amd64.zip` |

Extract and move the binary to your `$PATH`:

```bash
tar -xzf close-wiki_darwin_arm64.tar.gz
mv close-wiki /usr/local/bin/
```

## Usage

```bash
# Scan a repository and generate wiki
close-wiki scan --path /path/to/repo

# Serve the wiki locally
close-wiki serve --path /path/to/repo

# Ask questions about the codebase
close-wiki ask --path /path/to/repo "How does the authentication work?"

# Update wiki after code changes
close-wiki update --path /path/to/repo

# Scan specific languages only
close-wiki scan --path /path/to/repo --languages go,python,typescript
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

See the [main repository](https://github.com/unrealandychan/close-wiki) for full documentation, Python package, and advanced usage.
