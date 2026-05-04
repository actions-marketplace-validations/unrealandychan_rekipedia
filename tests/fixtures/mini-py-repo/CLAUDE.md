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
