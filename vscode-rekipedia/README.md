# Rekipedia VS Code Extension

AI-powered codebase intelligence directly in VS Code — Ask, Search, Browse Wiki, and Scan — powered by [rekipedia](https://github.com/unrealandychan/rekipedia).

## Features

### 💬 reki: Ask
Chat with your codebase. Type a question and get grounded answers with `file:line` citations you can click to jump directly to the source.

### 🔍 reki: Search Symbols
Instant symbol search across your entire codebase. Debounced live search as you type, opens file at exact line.

### 📚 Wiki Sidebar
Browse your auto-generated rekipedia wiki pages in the VS Code Explorer sidebar.

### 🔄 reki: Scan Workspace
Trigger a full rekipedia scan from inside VS Code. Progress shown in notification.

### 🔎 Symbol Hover
Hover over any symbol to see a rekipedia summary and jump to definition.

## Requirements

- [rekipedia](https://github.com/unrealandychan/rekipedia) installed locally
  ```bash
  pip install rekipedia
  ```
- A scanned workspace (run `reki scan .` once)

## Extension Settings

| Setting | Default | Description |
|---|---|---|
| `rekipedia.rekiPath` | `` | Path to reki binary. Auto-detects from venv or PATH if empty. |
| `rekipedia.wikiDir` | `docs/wiki` | Relative path to wiki directory. |
| `rekipedia.autoScan` | `false` | Auto-scan on workspace open. |

## Getting Started

1. Install rekipedia: `pip install rekipedia`
2. Scan your project: `reki scan .`
3. Open VS Code in the project folder
4. Run **reki: Ask** from the Command Palette (`Cmd+Shift+P`)

## Commands

| Command | Description |
|---|---|
| `Rekipedia: Ask` | Open chat panel |
| `Rekipedia: Search Symbols` | Open symbol Quick Pick |
| `Rekipedia: Scan Workspace` | Run full scan |
| `Rekipedia: Refresh Wiki` | Refresh wiki sidebar |

## License

MIT — part of the [rekipedia](https://github.com/unrealandychan/rekipedia) project.
