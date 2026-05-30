# VS Code Extension Implementation Plan

> **Goal:** A native VS Code extension (`vscode-rekipedia`) that surfaces rekipedia's core powers — Ask, Search, Wiki Browse, and Scan — directly inside the editor, without leaving VS Code.

---

## Architecture Overview

```
vscode-rekipedia/           ← Extension root (TypeScript, esbuild)
├── src/
│   ├── extension.ts        ← Activate/deactivate, register all providers
│   ├── reki.ts             ← Thin wrapper: spawn reki CLI subprocesses
│   ├── providers/
│   │   ├── AskPanel.ts     ← Webview panel: chat-style Q&A
│   │   ├── SearchProvider.ts ← Quick Pick: symbol search
│   │   ├── WikiTreeProvider.ts ← TreeView: wiki pages sidebar
│   │   └── HoverProvider.ts  ← Inline hover: symbol definition on hover
│   └── util/
│       ├── findReki.ts     ← Locate reki binary (PATH / venv / bundled)
│       └── config.ts       ← Read workspace settings
├── package.json            ← contributes.commands, views, configuration
├── esbuild.js              ← Bundle for distribution
└── .vscodeignore
```

**How it talks to rekipedia:**
The extension shells out to the local `reki` CLI. No custom server required — `reki ask`, `reki search`, `reki serve`, `reki scan` are all available. For the Ask panel, stream output from `reki ask` via stdio. For search, parse JSON output of `reki search --json`. For wiki tree, read `docs/wiki/` markdown files (or call `reki export --format json`).

---

## Issues Breakdown

### Issue #201 — [ext] Scaffold VS Code extension package
**Labels:** vscode, scaffold

Set up the bare-minimum extension skeleton: `package.json`, `tsconfig.json`, `esbuild.js`, `src/extension.ts` with activate/deactivate stubs. CI: compile-only check in GitHub Actions.

**Files:**
- Create: `vscode-rekipedia/package.json`
- Create: `vscode-rekipedia/tsconfig.json`
- Create: `vscode-rekipedia/esbuild.js`
- Create: `vscode-rekipedia/src/extension.ts`
- Create: `vscode-rekipedia/.vscodeignore`
- Create: `.github/workflows/vscode-ci.yml`

---

### Issue #202 — [ext] reki binary discovery utility
**Labels:** vscode, core

`findReki.ts` — locate the `reki` binary in order: (1) workspace setting `rekipedia.rekiPath`, (2) active Python venv `./venv/bin/reki`, (3) `$PATH`. Returns path or throws a user-friendly error with install hint.

**Files:**
- Create: `vscode-rekipedia/src/util/findReki.ts`
- Create: `vscode-rekipedia/src/util/findReki.test.ts`

---

### Issue #203 — [ext] CLI subprocess wrapper (`reki.ts`)
**Labels:** vscode, core

Thin async wrapper over Node `child_process`:
- `runReki(args, cwd): Promise<string>` — captures stdout, rejects on non-zero exit
- `streamReki(args, cwd, onChunk): Promise<void>` — streams stdout line-by-line (for Ask)

**Files:**
- Create: `vscode-rekipedia/src/reki.ts`
- Create: `vscode-rekipedia/src/reki.test.ts`

---

### Issue #204 — [ext] `reki: Ask` webview panel
**Labels:** vscode, feature

Chat-style Ask panel (`AskPanel.ts`). Command: `rekipedia.ask`. Opens a webview with a text input; on submit, streams `reki ask "<query>" --json` output into a chat bubble. Shows file:line citations as clickable links that jump to source.

**Files:**
- Create: `vscode-rekipedia/src/providers/AskPanel.ts`
- Create: `vscode-rekipedia/media/ask.html` (webview HTML template)
- Modify: `vscode-rekipedia/src/extension.ts` (register command + panel)
- Modify: `vscode-rekipedia/package.json` (contributes.commands)

---

### Issue #205 — [ext] `reki: Search Symbols` Quick Pick
**Labels:** vscode, feature

Command: `rekipedia.search`. Opens VS Code Quick Pick, calls `reki search "<query>" --json` on each keystroke (debounced 200 ms). Selecting a result opens the file at the correct line.

**Files:**
- Create: `vscode-rekipedia/src/providers/SearchProvider.ts`
- Modify: `vscode-rekipedia/src/extension.ts`
- Modify: `vscode-rekipedia/package.json`

---

### Issue #206 — [ext] Wiki sidebar TreeView
**Labels:** vscode, feature

Activity bar icon + TreeView showing wiki pages from `docs/wiki/`. Clicking a page opens the markdown file in a preview tab. Supports refresh button (`rekipedia.refreshWiki`). Reads wiki dir path from workspace config `rekipedia.wikiDir` (default: `docs/wiki`).

**Files:**
- Create: `vscode-rekipedia/src/providers/WikiTreeProvider.ts`
- Create: `vscode-rekipedia/media/icon.svg` (activity bar icon)
- Modify: `vscode-rekipedia/src/extension.ts`
- Modify: `vscode-rekipedia/package.json` (contributes.views, contributes.viewsContainers)

---

### Issue #207 — [ext] Symbol hover provider
**Labels:** vscode, feature

On hover over any identifier, call `reki search "<word>" --json --kind function,class,method` and show the first result's docstring + file:line in a hover tooltip. Configurable via `rekipedia.enableHover` (default: true).

**Files:**
- Create: `vscode-rekipedia/src/providers/HoverProvider.ts`
- Modify: `vscode-rekipedia/src/extension.ts`
- Modify: `vscode-rekipedia/package.json` (contributes.configuration)

---

### Issue #208 — [ext] `reki: Scan workspace` command
**Labels:** vscode, feature

Command: `rekipedia.scan`. Runs `reki scan .` in a VS Code Terminal (so user sees live output). On completion, refreshes the wiki TreeView automatically.

**Files:**
- Modify: `vscode-rekipedia/src/extension.ts`
- Modify: `vscode-rekipedia/package.json`

---

### Issue #209 — [ext] Workspace configuration schema
**Labels:** vscode, config

Register all settings under `rekipedia.*` in `package.json` contributes.configuration:
- `rekipedia.rekiPath` — custom binary path
- `rekipedia.wikiDir` — wiki output directory (default: `docs/wiki`)
- `rekipedia.enableHover` — toggle hover provider (default: true)
- `rekipedia.model` — LLM model override (passed as `--model`)

**Files:**
- Modify: `vscode-rekipedia/package.json`
- Create: `vscode-rekipedia/src/util/config.ts`

---

### Issue #210 — [ext] Package, publish & README
**Labels:** vscode, release

- Write `vscode-rekipedia/README.md` with screenshots/GIF, install instructions, and feature list
- Add `vsce package` to CI
- Add publish step gated on tag push (requires `VSCE_PAT` secret)
- Update root `README.md` to mention the extension

**Files:**
- Create: `vscode-rekipedia/README.md`
- Create: `vscode-rekipedia/CHANGELOG.md`
- Modify: `.github/workflows/vscode-ci.yml`
- Modify: `README.md`

---

## Sequencing

```
#201 scaffold
  └─ #202 findReki
       └─ #203 subprocess wrapper
            ├─ #204 Ask panel
            ├─ #205 Search quick pick
            ├─ #206 Wiki tree
            ├─ #207 Hover provider
            └─ #208 Scan command
                 └─ #209 config schema
                      └─ #210 publish
```

## Open Questions

1. **Bundled vs external `reki`?** — For now require user to install rekipedia (`pip install rekipedia`). Future: bundle a pre-compiled Go binary via `vscode-rekipedia/bin/`.
2. **MCP server instead of CLI shelling?** — `reki mcp` already exposes `ask`, `search_nodes`, `get_context` as JSON-RPC. Could use that as transport instead of parsing CLI stdout. Worth exploring in a follow-up issue.
3. **Telemetry?** — Skip for v1.
