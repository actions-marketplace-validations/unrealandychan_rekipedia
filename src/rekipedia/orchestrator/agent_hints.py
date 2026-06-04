"""Generate agent hint files so AI coding assistants know about rekipedia."""
from __future__ import annotations

import json as _json
from pathlib import Path

_REKIPEDIA_SECTION = """\
## rekipedia Codebase Knowledge Base

This repository has been scanned by [rekipedia](https://github.com/unrealandychan/rekipedia).
A structured wiki, symbol index, and RAG embeddings are in `.rekipedia/`.

### Ask questions about this codebase

```bash
reki ask "<your question>"
# Examples:
reki ask "how does authentication work?"
reki ask "what is the entry point of the application?"
reki ask "which modules are most critical?"
```

### MCP server (for Claude Code, Cursor, and other MCP-aware agents)

```bash
reki mcp
```

Available MCP tools: `ask`, `search_nodes`, `get_context`, `get_relationships`, `get_hub_nodes`, `get_impact`

> Tip: `.mcp.json` in the repo root auto-configures the MCP server for Claude Code.
"""

_MARKER = "## rekipedia Codebase Knowledge Base"


def _write_hint_file(path: Path, content: str) -> bool:
    """Write or update hint file. Returns True if written."""
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if _MARKER in existing:
            return False  # already has rekipedia section
        updated = existing.rstrip() + "\n\n---\n\n" + content
        path.write_text(updated, encoding="utf-8")
    else:
        path.write_text(content, encoding="utf-8")
    return True


def write_agent_hints(repo_root: Path) -> list[Path]:
    """Write CLAUDE.md, AGENTS.md, .github/copilot-instructions.md."""
    written = []
    targets = [
        repo_root / "CLAUDE.md",
        repo_root / "AGENTS.md",
        repo_root / ".github" / "copilot-instructions.md",
    ]
    for path in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
        if _write_hint_file(path, _REKIPEDIA_SECTION):
            written.append(path)
    return written


def write_mcp_json(repo_root: Path) -> bool:
    """Write .mcp.json for Claude Code auto-discovery. Returns True if written/updated."""
    mcp_path = repo_root / ".mcp.json"

    rekipedia_entry = {
        "command": "reki",
        "args": ["mcp"],
        "description": "rekipedia codebase knowledge — ask questions, search symbols, get impact analysis"
    }

    if mcp_path.exists():
        try:
            data = _json.loads(mcp_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        servers = data.get("mcpServers", {})
        if "rekipedia" in servers:
            return False  # already configured
        servers["rekipedia"] = rekipedia_entry
        data["mcpServers"] = servers
    else:
        data = {"mcpServers": {"rekipedia": rekipedia_entry}}

    mcp_path.write_text(_json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return True


def update_gitignore(repo_root: Path) -> None:
    """Add .mcp.json to .gitignore if not already present."""
    gitignore = repo_root / ".gitignore"
    entry = ".mcp.json"
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        if entry not in content:
            gitignore.write_text(content.rstrip() + f"\n{entry}\n", encoding="utf-8")
    # If no .gitignore, don't create one — not our job
