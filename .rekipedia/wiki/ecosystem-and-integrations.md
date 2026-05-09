---
slug: ecosystem-and-integrations
title: "External Integrations, Plugins, and Ecosystem"
section: general
pin: false
importance: 50
created_at: 2026-05-09T02:24:09Z
rekipedia_version: 0.12.0
---

# External Integrations, Plugins, and Ecosystem

This page documents the project’s third-party dependencies, any observable integrations with external systems, the extension points exposed in code, and the ecosystem context visible from the repository’s documentation and tests. The analysis is based on `README.md`, `package.json`, `pyproject.toml`, `RELEASE-NOTES.md`, and the implementation/tests under `src/rekipedia/` and `tests/`.

## External Dependencies

The repository metadata indicates the package is `rekipedia` version `0.13.0` for both Python and npm naming purposes, and it exposes CLI entry points via `rekipedia = "rekipedia.cli:main"` and `reki = "rekipedia.cli:main"` in the provided evidence. The code and relationship graph also make several third-party/runtime dependencies visible.

| Library / Package | Version | Purpose | Evidence |
|---|---:|---|---|
| `litellm` | Not specified in analysis | LLM provider abstraction used for chat/completions and tool-calling flows in agentic answering and planning. Imported by [`rekipedia.orchestrator.agent_ask`](src/rekipedia/orchestrator/agent_ask.py#L1) and [`rekipedia.synthesis.agent_planner`](src/rekipedia/synthesis/agent_planner.py#L1). | [`rekipedia.orchestrator.agent_ask`](src/rekipedia/orchestrator/agent_ask.py#L1), [`rekipedia.synthesis.agent_planner`](src/rekipedia/synthesis/agent_planner.py#L1) |
| `pytest` | Not specified in analysis | Test runner for the repository’s behavioral coverage. | [`tests.test_agent_ask`](tests/test_agent_ask.py#L1) |
| `unittest.mock` | Standard library | Used heavily in tests to simulate LLM responses and errors. | [`tests.test_agent_ask`](tests/test_agent_ask.py#L1) |
| `json` | Standard library | Serialization/deserialization for LLM messages, symbols, and plan payloads. | [`rekipedia.orchestrator.run_ask`](src/rekipedia/orchestrator/run_ask.py#L1), [`rekipedia.synthesis.planner`](src/rekipedia/synthesis/planner.py#L1) |
| `pathlib` | Standard library | Filesystem traversal for wiki pages, symbols, and repo outputs. | [`rekipedia.orchestrator.run_ask`](src/rekipedia/orchestrator/run_ask.py#L1), [`rekipedia.orchestrator.agent_ask`](src/rekipedia/orchestrator/agent_ask.py#L1) |
| `re` | Standard library | Query keyword extraction and text scoring heuristics. | [`rekipedia.orchestrator.run_ask`](src/rekipedia/orchestrator/run_ask.py#L1), [`rekipedia.synthesis.planner`](src/rekipedia/synthesis/planner.py#L1) |
| `os` | Standard library | Environment-variable driven behavior, including agent mode selection. | [`rekipedia.orchestrator.run_ask`](src/rekipedia/orchestrator/run_ask.py#L1), [`tests.test_agent_ask`](tests/test_agent_ask.py#L1) |
| `threading` | Standard library | Used by the planner implementation to run planning progress signaling concurrently. | [`rekipedia.synthesis.planner`](src/rekipedia/synthesis/planner.py#L1) |
| `collections.abc` | Standard library | Typing/runtime support for callable collections and iterable interfaces. | [`rekipedia.synthesis.agent_planner`](src/rekipedia/synthesis/agent_planner.py#L1) |

A few important notes from the evidence:

- The static analysis did **not** include the full dependency metadata from `pyproject.toml`, so versions for third-party libraries beyond the package version itself are not reliably extractable here.
- The code strongly suggests the project depends on an internal `rekipedia.llm.client` abstraction rather than talking to provider SDKs directly in most places, but that module was not included in the file set, so its own external dependencies cannot be enumerated from this analysis.
- `rekipedia.storage.sqlite_store` and `rekipedia.rag.embedder` are internal modules, not third-party libraries, but they are important integration surfaces within the project architecture.

> **Sources:** `package.json`, `pyproject.toml`, `src/rekipedia/orchestrator/agent_ask.py` · L1–L382 · [`rekipedia.orchestrator.agent_ask`](src/rekipedia/orchestrator/agent_ask.py#L1), [`rekipedia.orchestrator.run_ask`](src/rekipedia/orchestrator/run_ask.py#L1), [`rekipedia.synthesis.agent_planner`](src/rekipedia/synthesis/agent_planner.py#L1), [`rekipedia.synthesis.planner`](src/rekipedia/synthesis/planner.py#L1), [`tests.test_agent_ask`](tests/test_agent_ask.py#L1)

## Integrations

The codebase integrates primarily with three kinds of external systems or service boundaries: LLM providers, the local repository/wiki store, and a retrieval/indexing layer. There is no evidence in the supplied files of networked SaaS integrations like GitHub, Slack, or databases outside the project’s own SQLite-backed store.

### LLM Provider / Chat Completion API

The most significant integration is with an LLM completion backend, accessed through [`LLMClient`](src/rekipedia/orchestrator/run_ask.py#L310) and [`LLMClient`](src/rekipedia/synthesis/planner.py#L180) wrappers and, in some paths, via direct `litellm` tool-calling responses. Two agentic modules rely on that interface:

- [`AgentAsk`](src/rekipedia/orchestrator/agent_ask.py#L253) implements a ReAct-style answer loop for codebase questions.
- [`AgentPlanner`](src/rekipedia/synthesis/agent_planner.py#L144) performs tool-calling planning to construct a [`WikiPlan`](src/rekipedia/synthesis/planner.py#L138).

**What it does**

- Generates the final user-facing answer grounded in repository context.
- Performs iterative tool calls such as `search_code`, `get_symbol`, `get_page`, and `get_relationships`.
- Creates planning decisions from a compact summary of files, diagrams, and structural hints.

**How it’s configured**

- The configuration object is an [`LLMConfig`](src/rekipedia/orchestrator/run_ask.py#L310) / [`LLMConfig`](src/rekipedia/synthesis/agent_planner.py#L151) passed into the orchestrators.
- Agent answering can be enabled via the `REKIPEDIA_AGENT_ASK` environment variable, which causes [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334) to delegate to [`agent_run_ask`](src/rekipedia/orchestrator/agent_ask.py#L371).
- The agent flow falls back to single-shot mode if the model does not support tool calling or if the client raises an exception, as documented in [`AgentAsk`](src/rekipedia/orchestrator/agent_ask.py#L253) and tested in [`test_agent_ask_fallback_on_error`](tests/test_agent_ask.py#L198).

**Code reference**

- [`AgentAsk.run`](src/rekipedia/orchestrator/agent_ask.py#L275)
- [`agent_run_ask`](src/rekipedia/orchestrator/agent_ask.py#L371)
- [`AgentPlanner.plan`](src/rekipedia/synthesis/agent_planner.py#L155)
- [`PlannerAgent.plan`](src/rekipedia/synthesis/planner.py#L186)

> **Sources:** `src/rekipedia/orchestrator/agent_ask.py` · L253–L382 · [`AgentAsk`](src/rekipedia/orchestrator/agent_ask.py#L253), [`agent_run_ask`](src/rekipedia/orchestrator/agent_ask.py#L371); `src/rekipedia/synthesis/agent_planner.py` · L144–L295 · [`AgentPlanner`](src/rekipedia/synthesis/agent_planner.py#L144); `src/rekipedia/synthesis/planner.py` · L180–L286 · [`PlannerAgent`](src/rekipedia/synthesis/planner.py#L180)

### Local SQLite Knowledge Store

The project uses a local SQLite-backed store as an internal integration boundary for scan results, page metadata, relationships, and note data. The store is accessed through [`SqliteStore`](src/rekipedia/orchestrator/run_ask.py#L1) in both answer and planning flows.

**What it does**

- Verifies that a successful scan exists before answering.
- Loads relationships for the latest successful run.
- Pulls note data and page metadata into the system prompt context.

**How it’s configured**

- The store path appears to be rooted under `output_dir`, which is described as the `.rekipedia/` directory containing `store.db` and wiki outputs in [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334).
- [`_verify_scan`](src/rekipedia/orchestrator/run_ask.py#L37) checks for a latest successful run and raises `RuntimeError` if none exists.
- [`_ToolHandler.get_relationships`](src/rekipedia/orchestrator/agent_ask.py#L208) and [`_build_full_system`](src/rekipedia/orchestrator/run_ask.py#L208) query the store for relationships and notes.

**Code reference**

- [`_verify_scan`](src/rekipedia/orchestrator/run_ask.py#L37)
- [`_load_symbol_lines`](src/rekipedia/orchestrator/run_ask.py#L66)
- [`_build_full_system`](src/rekipedia/orchestrator/run_ask.py#L208)
- [`_ToolHandler.get_relationships`](src/rekipedia/orchestrator/agent_ask.py#L208)

> **Sources:** `src/rekipedia/orchestrator/run_ask.py` · L37–L361 · [`_verify_scan`](src/rekipedia/orchestrator/run_ask.py#L37), [`_build_full_system`](src/rekipedia/orchestrator/run_ask.py#L208), [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334); `src/rekipedia/orchestrator/agent_ask.py` · L208–L246 · [`_ToolHandler.get_relationships`](src/rekipedia/orchestrator/agent_ask.py#L208)

### Retrieval / RAG Index

The answer pipeline optionally integrates with a retrieval layer through [`EmbedPipeline`](src/rekipedia/orchestrator/run_ask.py#L86), which is queried in [`_rag_chunks`](src/rekipedia/orchestrator/run_ask.py#L86). This acts as the semantic search layer for repository chunks.

**What it does**

- Retrieves top-k code chunks relevant to the question.
- Supplements the system prompt with textual evidence from the codebase.
- Is used both in the standard answer path and exposed as a tool via [`_ToolHandler.search_code`](src/rekipedia/orchestrator/agent_ask.py#L160).

**How it’s configured**

- [`_rag_chunks`](src/rekipedia/orchestrator/run_ask.py#L86) returns an empty list if the index is not available.
- The agent tool returns `"No code chunks found"` when the index is absent, which is verified by [`test_tool_handler_search_code_no_index`](tests/test_agent_ask.py#L60).
- Top-k selection is query-driven and normalized by keyword extraction in [`_extract_keywords`](src/rekipedia/orchestrator/run_ask.py#L104).

**Code reference**

- [`_rag_chunks`](src/rekipedia/orchestrator/run_ask.py#L86)
- [`_ToolHandler.search_code`](src/rekipedia/orchestrator/agent_ask.py#L160)
- [`_score_page`](src/rekipedia/orchestrator/run_ask.py#L116)

> **Sources:** `src/rekipedia/orchestrator/run_ask.py` · L86–L146 · [`_rag_chunks`](src/rekipedia/orchestrator/run_ask.py#L86), [`_score_page`](src/rekipedia/orchestrator/run_ask.py#L116); `src/rekipedia/orchestrator/agent_ask.py` · L160–L171 · [`_ToolHandler.search_code`](src/rekipedia/orchestrator/agent_ask.py#L160)

## Extension Points

The repository contains several extension mechanisms, mostly implemented as agent tools and planner callbacks rather than a formal plugin registry.

### Tool Dispatch in `AgentAsk`

The clearest extension point is the private tool handler class [`_ToolHandler`](src/rekipedia/orchestrator/agent_ask.py#L141), which centralizes all callable tools exposed to the LLM agent.

Supported tools observed in the analysis:

- `search_code`
- `get_symbol`
- `get_page`
- `get_relationships`

These are routed through [`_ToolHandler.dispatch`](src/rekipedia/orchestrator/agent_ask.py#L236), which selects the implementation based on `tool_name`.

This is effectively a plugin surface for adding new assistant capabilities: a developer would add a method and wire it into `dispatch`, and then expose it in the agent prompt / tool schema.

**Observable constraints**

- The handler is private (`_ToolHandler`), so it is an internal extension surface, not a public plugin API.
- Tool responses are plain strings, suggesting a lightweight, text-first contract.

**Code reference**

- [`_ToolHandler`](src/rekipedia/orchestrator/agent_ask.py#L141)
- [`_ToolHandler.dispatch`](src/rekipedia/orchestrator/agent_ask.py#L236)
- [`AgentAsk.run`](src/rekipedia/orchestrator/agent_ask.py#L275)

> **Sources:** `src/rekipedia/orchestrator/agent_ask.py` · L141–L246 · [`_ToolHandler`](src/rekipedia/orchestrator/agent_ask.py#L141), [`_ToolHandler.dispatch`](src/rekipedia/orchestrator/agent_ask.py#L236)

### Planning Callbacks

Planning supports a progress callback hook:

- [`PlannerAgent.plan`](src/rekipedia/synthesis/planner.py#L186) accepts `progress_cb`.
- [`AgentPlanner.plan`](src/rekipedia/synthesis/agent_planner.py#L155) also accepts `progress_cb`.

This allows callers to animate a spinner, surface status updates, or integrate with a UI without changing the planner itself. The docstring on [`PlannerAgent.plan`](src/rekipedia/synthesis/planner.py#L186) explicitly notes that the callback is called with status strings during a blocking LLM call.

**Practical extension use**

- UI/CLI status reporting
- Telemetry hooks
- Progress logging in long-running planning flows

**Code reference**

- [`PlannerAgent.plan`](src/rekipedia/synthesis/planner.py#L186)
- [`AgentPlanner.plan`](src/rekipedia/synthesis/agent_planner.py#L155)

> **Sources:** `src/rekipedia/synthesis/planner.py` · L186–L286 · [`PlannerAgent.plan`](src/rekipedia/synthesis/planner.py#L186); `src/rekipedia/synthesis/agent_planner.py` · L155–L295 · [`AgentPlanner.plan`](src/rekipedia/synthesis/agent_planner.py#L155)

### Fallback Planning and Answering Modes

The code includes built-in fallback behaviors that act like “graceful extension points”:

- [`PlannerAgent.plan`](src/rekipedia/synthesis/planner.py#L186) falls back to [`_default_plan`](src/rekipedia/synthesis/planner.py#L400) if the LLM call fails.
- [`AgentPlanner.plan`](src/rekipedia/synthesis/agent_planner.py#L155) also falls back to [`_default_plan`](src/rekipedia/synthesis/planner.py#L400).
- [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334) can delegate to [`agent_run_ask`](src/rekipedia/orchestrator/agent_ask.py#L371) based on `REKIPEDIA_AGENT_ASK`.

These modes are not plugins in the classic sense, but they provide configurability without changing public APIs.

> **Sources:** `src/rekipedia/synthesis/planner.py` · L186–L495 · [`PlannerAgent.plan`](src/rekipedia/synthesis/planner.py#L186), [`_default_plan`](src/rekipedia/synthesis/planner.py#L400); `src/rekipedia/synthesis/agent_planner.py` · L155–L295 · [`AgentPlanner.plan`](src/rekipedia/synthesis/agent_planner.py#L155); `src/rekipedia/orchestrator/run_ask.py` · L334–L361 · [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334)

## Related Projects

The repository itself does not enumerate “similar projects” in a dedicated comparison section, so this section is limited to inference from the code and README-style usage patterns.

### Evident Ecosystem Neighbors

Based on the architecture and naming, this project sits in the same broad category as:

| Project type | Why it appears related | Evidence level |
|---|---|---|
| Codebase Q&A assistants | The answer flow retrieves code chunks, wiki pages, symbols, and relationships, then asks an LLM to answer grounded in the repository. | High |
| Repository documentation generators | The planner produces a `WikiPlan`, and the synthesis layer generates wiki structure from analysis results. | High |
| RAG-enhanced developer copilots | The presence of `EmbedPipeline`, `search_code`, and symbol/page retrieval indicates retrieval-augmented generation over source code. | High |
| Agentic “tool-calling” LLM apps | The `AgentAsk` and `AgentPlanner` classes implement tool-call loops and fallback modes. | High |

### What the README/Docs Suggest

The supplied file list includes `README.md` and `RELEASE-NOTES.md`, but the analysis payload did not include their full text, so I cannot quote explicit comparisons or named external projects. If the README contains a “Similar tools” or “Inspired by” section, that would be the best place to expand this segment.

> **Sources:** `README.md`, `RELEASE-NOTES.md`; `src/rekipedia/orchestrator/agent_ask.py` · L253–L382 · [`AgentAsk`](src/rekipedia/orchestrator/agent_ask.py#L253); `src/rekipedia/orchestrator/run_ask.py` · L86–L377 · [`_rag_chunks`](src/rekipedia/orchestrator/run_ask.py#L86), [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334); `src/rekipedia/synthesis/planner.py` · L138–L495 · [`WikiPlan`](src/rekipedia/synthesis/planner.py#L138), [`PlannerAgent`](src/rekipedia/synthesis/planner.py#L180)

## Roadmap / Known Limitations

No explicit `TODO` or `FIXME` markers were surfaced in the supplied analysis, and the `risks` list is empty. However, several practical limitations and risk items are visible from the implementation and test coverage.

### Observed Limitations

| Limitation | Evidence | Impact |
|---|---|---|
| Agent mode is opt-in via environment variable | `test_run_ask_uses_agent_when_env_set` confirms `REKIPEDIA_AGENT_ASK=1` changes behavior. | Users may not discover the agentic path unless documented. |
| Retrieval may be unavailable | `_rag_chunks` can return `[]`, and the agent tool reports `"No code chunks found"`. | Answer quality degrades when the index is absent or incomplete. |
| Fallbacks hide LLM failures | Both planners and the answer flow can fall back to heuristic or single-shot behavior. | Improves robustness, but may mask degradation unless logged carefully. |
| Some core functions lack test coverage | `knowledge_gaps` flags [`_default_plan`](src/rekipedia/synthesis/planner.py#L400) and [`WikiPlan`](src/rekipedia/synthesis/planner.py#L138). | Increases regression risk around fallback planning and plan representation. |
| The plugin surface is internal, not formalized | `_ToolHandler` is private and tool wiring is implicit. | Extensibility is possible but requires code changes. |

### Notable Risk Items from Analysis

The strongest evidence-based risks come from the hub/knowledge-gap data:

- [`_default_plan`](src/rekipedia/synthesis/planner.py#L400) is called multiple times and has **no direct test coverage**.
- [`WikiPlan`](src/rekipedia/synthesis/planner.py#L138) is also uncovered by direct tests despite being central to the planning output.
- [`_build_full_system`](src/rekipedia/orchestrator/run_ask.py#L208) is a high-degree bridge function that assembles many context sources; it is therefore sensitive to changes in file formats, store layout, and ranking heuristics.

### What Is Not Yet Evidenced

- No explicit roadmap items were present in the supplied `RELEASE-NOTES.md` analysis.
- No open-ended TODO/FIXME markers were included in the static analysis payload.
- No external ecosystem integrations beyond LLMs and local repo infrastructure were visible.

> **Sources:** `tests/test_agent_ask.py` · L283–L303 · [`test_run_ask_uses_agent_when_env_set`](tests/test_agent_ask.py#L283); `src/rekipedia/synthesis/planner.py` · L138–L495 · [`WikiPlan`](src/rekipedia/synthesis/planner.py#L138), [`_default_plan`](src/rekipedia/synthesis/planner.py#L400), [`PlannerAgent.plan`](src/rekipedia/synthesis/planner.py#L186); `src/rekipedia/orchestrator/run_ask.py` · L86–L377 · [`_rag_chunks`](src/rekipedia/orchestrator/run_ask.py#L86), [`_build_full_system`](src/rekipedia/orchestrator/run_ask.py#L208), [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334)