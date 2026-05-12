# Agentic Ask — ReAct Tool-Calling Loop

**Source:** `src/rekipedia/orchestrator/agent_ask.py`
**Activated by:** `REKIPEDIA_AGENT_ASK=1` env var
**Used by:** `reki ask` (agentic mode)

## Overview

Instead of dumping the entire wiki + symbol index into the LLM context (the "96K context anti-pattern"), the agentic ask loop lets the LLM **fetch exactly what it needs** via tool calls — ReAct style (Reason + Act).

## Tools Available to the LLM

| Tool | Description |
|---|---|
| `search_code(query, top_k=5)` | RAG semantic search over source chunks |
| `get_symbol(name)` | Symbol location + signature from SQLite |
| `get_page(slug)` | Full wiki page content (markdown) |
| `get_relationships(target)` | Dependency graph for a symbol/file |
| `finish(answer)` | Provide final answer — terminates the loop |

## Loop

```
max_iter = REKIPEDIA_ASK_MAX_ITER (default: 5)

messages = [system_prompt, user_question]

for iteration in range(max_iter):
    response = litellm.completion(messages, tools=TOOLS)

    if no tool calls:
        return response.content   # LLM answered directly

    for tool_call in response.tool_calls:
        if tool_call.name == "finish":
            return tool_call.args["answer"]

        result = dispatch_tool(tool_call)
        messages.append(tool_result(tool_call.id, result))

# Fallback: return last message content if max_iter reached
```

## Why ReAct Over Single-Shot?

| Approach | Context used | Quality |
|---|---|---|
| Dump everything | 96K+ tokens | High recall, low precision, expensive |
| Single RAG retrieval | ~5K tokens | Miss multi-hop questions |
| **ReAct loop (current)** | ~5–20K tokens | Handles multi-hop, precise, cheaper |

**Example multi-hop query:** *"How does the embedder handle arm64 fallback when FAISS is unavailable?"*
- Iteration 1: `search_code("faiss arm64 fallback")` → finds `embedder.py` reference
- Iteration 2: `get_symbol("_numpy_cosine_search")` → gets exact implementation
- Iteration 3: `finish(answer)`

## Configuration

| Variable | Default | Effect |
|---|---|---|
| `REKIPEDIA_AGENT_ASK` | `0` | Enable agentic mode |
| `REKIPEDIA_ASK_MAX_ITER` | `5` | Max tool-call iterations |

## Termination Conditions

1. LLM calls `finish(answer)` — clean exit
2. LLM returns text with no tool calls — treated as final answer
3. `max_iter` reached — returns last available content

## Known Limitations

| Limitation | Detail |
|---|---|
| No parallel tool calls | Iterations are sequential — could parallelise independent calls |
| Fixed max_iter | No adaptive stopping (e.g. "confidence threshold") |
| No memory across sessions | Each `reki ask` starts fresh |

## Integration Points

- `agent_ask.py` is the agentic path; `run_ask.py` is the simpler single-shot path
- Both paths share: `_load_wiki_pages()`, `_rag_chunks()`, `_load_symbol_lines()`
- MCP server exposes the same tools as MCP protocol endpoints
