---
slug: cli-and-api
title: "CLI Reference and Programmatic API"
section: general
pin: false
importance: 50
created_at: 2026-05-09T02:23:44Z
rekipedia_version: 0.12.0
---

# CLI Reference and Programmatic API

## Overview

This page documents the externally useful command-line and Python entry points that are visible in the analyzed repository snapshot. The package metadata in `package.json` and `pyproject.toml` shows the project name/version as `rekipedia 0.13.0`, and the installed console scripts are:

```text
rekipedia = "rekipedia.cli:main"
reki = "rekipedia.cli:main"
```

Those entry points are declared, but the actual CLI implementation file (`rekipedia/cli.py`) is not present in the provided analysis set, so this page can only document the command surface that is evidenced indirectly by the repository metadata and the APIs exposed in the implementation files. The most concrete public programmatic APIs available in the analyzed code are the question-answering and planning functions/classes in `src/rekipedia/orchestrator/run_ask.py`, `src/rekipedia/orchestrator/agent_ask.py`, `src/rekipedia/synthesis/planner.py`, and `src/rekipedia/synthesis/agent_planner.py`.

The test file [`tests/test_agent_ask.py`](tests/test_agent_ask.py#L1) also provides behavioral evidence for how these APIs are intended to be used, especially the environment-controlled agentic ask path (`REKIPEDIA_AGENT_ASK=1`) and the planner fallback behavior.

> **Sources:** `package.json` · `pyproject.toml` · `src/rekipedia/orchestrator/run_ask.py` · `src/rekipedia/orchestrator/agent_ask.py` · `src/rekipedia/synthesis/planner.py` · `src/rekipedia/synthesis/agent_planner.py`

## CLI Reference

The repository metadata proves that the CLI is invoked via `rekipedia` or `reki`, both bound to `rekipedia.cli:main`, but the command parser itself is not included in the analyzed files. As a result, the specific subcommands and flags cannot be enumerated from the source evidence available here. What can be stated safely is that the CLI entry point exists and is meant to front the core orchestration APIs documented below.

### `rekipedia`

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| *(unknown from analyzed sources)* |  |  | The CLI entry point exported as `rekipedia.cli:main` in package metadata. The actual subcommands/flags are not present in the analysis payload, so no verified option list can be reconstructed. |

Usage example:

```bash
rekipedia --help
```

### `reki`

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| *(unknown from analyzed sources)* |  |  | Alias entry point for the same `rekipedia.cli:main` function. |

Usage example:

```bash
reki --help
```

### Practical CLI-to-API mapping

Although the parser is not visible, the exported console scripts almost certainly wrap the same internal workflows exposed by:

- [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334)
- [`stream_ask`](src/rekipedia/orchestrator/run_ask.py#L364)
- [`agent_run_ask`](src/rekipedia/orchestrator/agent_ask.py#L371)

This is supported by the test [`test_run_ask_uses_agent_when_env_set`](tests/test_agent_ask.py#L283), which verifies that `run_ask` delegates to [`agent_run_ask`](src/rekipedia/orchestrator/agent_ask.py#L371) when the environment variable `REKIPEDIA_AGENT_ASK=1` is set.

> **Sources:** `package.json` · `pyproject.toml` · `src/rekipedia/orchestrator/run_ask.py` · `src/rekipedia/orchestrator/agent_ask.py` · [`test_run_ask_uses_agent_when_env_set`](tests/test_agent_ask.py#L283)

## Programmatic API

The following functions and classes are the documented external-facing APIs evidenced by the repository. They are the main integration points for application code.

### [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334)

**Signature:** `run_ask(question, repo_root, output_dir, llm_config, history)`

Answers a free-text question against the indexed repository knowledge store and returns a Markdown response string. The docstring explicitly says it is grounded in the knowledge store and raises `RuntimeError` when no successful scan exists.

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | string | User’s free-text question. |
| `repo_root` | path/string | Absolute path to the repository being queried. |
| `output_dir` | path/string | `.rekipedia/` directory containing `store.db` and `wiki/`. |
| `llm_config` | `LLMConfig`-like | LLM settings; defaults are implied by `LLMConfig()`. |
| `history` | list of `{role, content}` | Previous conversation turns. |

**Return value:** Markdown string containing the assistant answer.

Example:

```python
from rekipedia.orchestrator.run_ask import run_ask
from rekipedia.models.contracts import LLMConfig

answer = run_ask(
    question="What does the planner do when the LLM fails?",
    repo_root="/path/to/repo",
    output_dir="/path/to/repo/.rekipedia",
    llm_config=LLMConfig(),
    history=[],
)
print(answer)
```

Implementation notes visible in the source:
- It uses [`_prepare_ask`](src/rekipedia/orchestrator/run_ask.py#L310) to validate the scan and build the prompt.
- It conditionally delegates to [`agent_run_ask`](src/rekipedia/orchestrator/agent_ask.py#L371) if agent mode is enabled.
- The test [`test_run_ask_uses_agent_when_env_set`](tests/test_agent_ask.py#L283) confirms that environment-based switch.

> **Sources:** `src/rekipedia/orchestrator/run_ask.py` · L334–L361 · [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334) · [`_prepare_ask`](src/rekipedia/orchestrator/run_ask.py#L310) · [`agent_run_ask`](src/rekipedia/orchestrator/agent_ask.py#L371) · [`test_run_ask_uses_agent_when_env_set`](tests/test_agent_ask.py#L283)

### [`stream_ask`](src/rekipedia/orchestrator/run_ask.py#L364)

**Signature:** `stream_ask(question, repo_root, output_dir, llm_config, history)`

Streaming variant of `run_ask`. The docstring says it is identical to `run_ask` except the final LLM call uses streaming and yields text chunks rather than returning one string.

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | string | User question. |
| `repo_root` | path/string | Repository root path. |
| `output_dir` | path/string | Knowledge store directory. |
| `llm_config` | `LLMConfig`-like | LLM settings. |
| `history` | list of `{role, content}` | Prior turns. |

**Return value:** A streaming iterator/generator of text chunks.

Example:

```python
from rekipedia.orchestrator.run_ask import stream_ask
from rekipedia.models.contracts import LLMConfig

for chunk in stream_ask(
    "Summarize the ask pipeline.",
    "/path/to/repo",
    "/path/to/repo/.rekipedia",
    LLMConfig(),
    [],
):
    print(chunk, end="")
```

> **Sources:** `src/rekipedia/orchestrator/run_ask.py` · L364–L377 · [`stream_ask`](src/rekipedia/orchestrator/run_ask.py#L364)

### [`agent_run_ask`](src/rekipedia/orchestrator/agent_ask.py#L371)

**Signature:** `agent_run_ask(question, repo_root, output_dir, llm_config, history)`

Agentic version of `run_ask`. The function delegates to [`AgentAsk`](src/rekipedia/orchestrator/agent_ask.py#L253), which runs a ReAct-style tool-using loop.

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | string | User question. |
| `repo_root` | path/string | Repository root. |
| `output_dir` | path/string | `.rekipedia/` directory. |
| `llm_config` | `LLMConfig`-like | LLM configuration. |
| `history` | list of `{role, content}` | Conversation history. |

**Return value:** Markdown answer string.

Example:

```python
from rekipedia.orchestrator.agent_ask import agent_run_ask
from rekipedia.models.contracts import LLMConfig

answer = agent_run_ask(
    "Where are relationships loaded from?",
    "/path/to/repo",
    "/path/to/repo/.rekipedia",
    LLMConfig(),
    [],
)
print(answer)
```

Behavioral evidence:
- [`AgentAsk.run`](src/rekipedia/orchestrator/agent_ask.py#L275) implements the loop.
- Tests cover direct-answer mode, tool-call mode, finish-tool mode, max-iteration fallback, and error fallback.

> **Sources:** `src/rekipedia/orchestrator/agent_ask.py` · L371–L382 · [`agent_run_ask`](src/rekipedia/orchestrator/agent_ask.py#L371) · [`AgentAsk.run`](src/rekipedia/orchestrator/agent_ask.py#L275) · [`tests/test_agent_ask.py`](tests/test_agent_ask.py#L112)

### [`AgentAsk`](src/rekipedia/orchestrator/agent_ask.py#L253)

**Signature:** `class AgentAsk`

ReAct agentic loop for answering codebase questions. The class docstring notes that it falls back to single-shot mode if the model does not support tool calling.

#### Constructor

**Signature:** `__init__(self, output_dir, llm_config)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `output_dir` | path/string | Knowledge store directory. |
| `llm_config` | `LLMConfig`-like | LLM settings. |

#### `run`

**Signature:** `run(self, question, history, max_iter)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | string | User question to answer. |
| `history` | list | Prior conversation turns. |
| `max_iter` | integer | Maximum tool-use iterations before final fallback. |

**Return value:** Markdown string.

Example:

```python
from rekipedia.orchestrator.agent_ask import AgentAsk
from rekipedia.models.contracts import LLMConfig

agent = AgentAsk("/path/to/repo/.rekipedia", LLMConfig())
answer = agent.run("How do I inspect symbol relationships?", [], max_iter=4)
print(answer)
```

#### Internal tool handler

The agent uses a private helper [`_ToolHandler`](src/rekipedia/orchestrator/agent_ask.py#L141) with methods:

- [`search_code`](src/rekipedia/orchestrator/agent_ask.py#L160)
- [`get_symbol`](src/rekipedia/orchestrator/agent_ask.py#L173)
- [`get_page`](src/rekipedia/orchestrator/agent_ask.py#L189)
- [`get_relationships`](src/rekipedia/orchestrator/agent_ask.py#L208)
- [`dispatch`](src/rekipedia/orchestrator/agent_ask.py#L236)

These are not public APIs, but they explain what the agent can do: search RAG chunks, retrieve symbol metadata from `symbols.json`, read wiki pages, and inspect stored relationships through [`SqliteStore`](src/rekipedia/orchestrator/agent_ask.py#L141).

> **Sources:** `src/rekipedia/orchestrator/agent_ask.py` · L141–L364 · [`AgentAsk`](src/rekipedia/orchestrator/agent_ask.py#L253) · [`_ToolHandler`](src/rekipedia/orchestrator/agent_ask.py#L141) · [`_ToolHandler.search_code`](src/rekipedia/orchestrator/agent_ask.py#L160) · [`_ToolHandler.get_symbol`](src/rekipedia/orchestrator/agent_ask.py#L173) · [`_ToolHandler.get_page`](src/rekipedia/orchestrator/agent_ask.py#L189) · [`_ToolHandler.get_relationships`](src/rekipedia/orchestrator/agent_ask.py#L208)

### [`WikiPlan`](src/rekipedia/synthesis/planner.py#L138)

**Signature:** `class WikiPlan`

Structured output of the planner used to drive wiki generation.

#### Constructor

**Signature:** `__init__(self, data)`

The constructor normalizes the supplied data into internal page and section structures.

| Parameter | Type | Description |
|-----------|------|-------------|
| `data` | mapping/dict | Raw plan payload produced by planner logic or LLM output. |

#### Methods

- [`get_page`](src/rekipedia/synthesis/planner.py#L166)
- [`get_section_for`](src/rekipedia/synthesis/planner.py#L169)
- [`__repr__`](src/rekipedia/synthesis/planner.py#L175)

**Return value:** Object-oriented access to the wiki plan, with convenience lookup helpers.

Example:

```python
from rekipedia.synthesis.planner import WikiPlan

plan = WikiPlan({
    "pages": [{"slug": "architecture", "title": "Architecture"}],
    "sections": [{"page_slug": "architecture", "title": "Overview"}],
})
print(plan.get_page("architecture"))
print(plan.get_section_for("architecture"))
```

Note: the analysis reveals that [`WikiPlan`](src/rekipedia/synthesis/planner.py#L138) has no dedicated test coverage in `tests/test_agent_ask.py`, which is tracked as a knowledge gap.

> **Sources:** `src/rekipedia/synthesis/planner.py` · L138–L177 · [`WikiPlan`](src/rekipedia/synthesis/planner.py#L138) · [`WikiPlan.get_page`](src/rekipedia/synthesis/planner.py#L166) · [`WikiPlan.get_section_for`](src/rekipedia/synthesis/planner.py#L169) · [`WikiPlan.__repr__`](src/rekipedia/synthesis/planner.py#L175)

### [`PlannerAgent`](src/rekipedia/synthesis/planner.py#L180)

**Signature:** `class PlannerAgent`

One-shot LLM planner that designs the entire wiki structure.

#### Constructor

**Signature:** `__init__(self, llm_config)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `llm_config` | `LLMConfig`-like | LLM settings used by the client. |

#### `plan`

**Signature:** `plan(self, combined, diagrams, progress_cb)`

The docstring says this analyses the combined repository snapshot and returns a [`WikiPlan`](src/rekipedia/synthesis/planner.py#L138). It accepts a progress callback to support UI spinners during the blocking LLM call and falls back to a sensible default plan if the LLM call fails.

| Parameter | Type | Description |
|-----------|------|-------------|
| `combined` | mapping/dict | Repository snapshot/analysis payload. |
| `diagrams` | list | Diagram metadata or diagram descriptions. |
| `progress_cb` | callable | Called with status strings during planning. |

**Return value:** [`WikiPlan`](src/rekipedia/synthesis/planner.py#L138)

Example:

```python
from rekipedia.synthesis.planner import PlannerAgent
from rekipedia.models.contracts import LLMConfig

planner = PlannerAgent(LLMConfig())
plan = planner.plan(
    combined={"files_seen": ["src/foo.py"]},
    diagrams=[],
    progress_cb=lambda msg: print(msg),
)
print(plan)
```

The implementation evidence shows this method may call [`_default_plan`](src/rekipedia/synthesis/planner.py#L400) when the model fails. The test [`test_agent_planner_fallback_on_error`](tests/test_agent_ask.py#L263) verifies that fallback behavior.

> **Sources:** `src/rekipedia/synthesis/planner.py` · L180–L286 · [`PlannerAgent`](src/rekipedia/synthesis/planner.py#L180) · [`PlannerAgent.plan`](src/rekipedia/synthesis/planner.py#L186) · [`_default_plan`](src/rekipedia/synthesis/planner.py#L400) · [`tests/test_agent_ask.py`](tests/test_agent_ask.py#L263)

### [`AgentPlanner`](src/rekipedia/synthesis/agent_planner.py#L144)

**Signature:** `class AgentPlanner`

Tool-calling planner for wiki structure design. Its class docstring says it has the same interface as `PlannerAgent`: constructor takes `llm_config`, and `.plan()` returns [`WikiPlan`](src/rekipedia/synthesis/planner.py#L138).

#### Constructor

**Signature:** `__init__(self, llm_config)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `llm_config` | `LLMConfig`-like | LLM configuration. |

#### `plan`

**Signature:** `plan(self, combined, diagrams, progress_cb)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `combined` | mapping/dict | Repository snapshot or combined analysis payload. |
| `diagrams` | list | Diagram metadata. |
| `progress_cb` | callable | Progress update callback. |

**Return value:** [`WikiPlan`](src/rekipedia/synthesis/planner.py#L138)

Example:

```python
from rekipedia.synthesis.agent_planner import AgentPlanner
from rekipedia.models.contracts import LLMConfig

planner = AgentPlanner(LLMConfig())
plan = planner.plan(
    combined={"files_seen": ["src/foo.py"]},
    diagrams=[],
    progress_cb=print,
)
print(plan)
```

The tests show this agent can emit tool-driven pages/sections and still return a valid [`WikiPlan`](src/rekipedia/synthesis/planner.py#L138).

> **Sources:** `src/rekipedia/synthesis/agent_planner.py` · L144–L295 · [`AgentPlanner`](src/rekipedia/synthesis/agent_planner.py#L144) · [`AgentPlanner.plan`](src/rekipedia/synthesis/agent_planner.py#L155) · [`WikiPlan`](src/rekipedia/synthesis/planner.py#L138) · [`tests/test_agent_ask.py`](tests/test_agent_ask.py#L220)

## Integration Examples

The repository’s structure suggests a clean split between orchestration and planning. A practical workflow is:

1. Run a scan/build phase externally to create `.rekipedia/store.db` and wiki pages.
2. Use [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334) for standard Q&A.
3. Switch to [`agent_run_ask`](src/rekipedia/orchestrator/agent_ask.py#L371) or set `REKIPEDIA_AGENT_ASK=1` when you want iterative tool use.
4. Use [`PlannerAgent`](src/rekipedia/synthesis/planner.py#L180) or [`AgentPlanner`](src/rekipedia/synthesis/agent_planner.py#L144) when constructing or regenerating the wiki structure.

### End-to-end example: generate, then ask

```python
from rekipedia.synthesis.planner import PlannerAgent
from rekipedia.orchestrator.run_ask import run_ask
from rekipedia.models.contracts import LLMConfig

repo_root = "/path/to/repo"
output_dir = "/path/to/repo/.rekipedia"
llm_config = LLMConfig()

# Step 1: plan wiki structure
planner = PlannerAgent(llm_config)
plan = planner.plan(
    combined={"files_seen": ["src/rekipedia/orchestrator/run_ask.py"]},
    diagrams=[],
    progress_cb=lambda msg: print(f"[plan] {msg}"),
)

# Step 2: answer a question against the generated knowledge store
answer = run_ask(
    question="How does ask mode build its context?",
    repo_root=repo_root,
    output_dir=output_dir,
    llm_config=llm_config,
    history=[],
)

print(plan)
print(answer)
```

### Agentic ask workflow

If you need the assistant to inspect symbols/pages/relationships interactively, use the agentic API:

```python
from rekipedia.orchestrator.agent_ask import agent_run_ask
from rekipedia.models.contracts import LLMConfig

answer = agent_run_ask(
    "Show me the relationship-loading path.",
    "/path/to/repo",
    "/path/to/repo/.rekipedia",
    LLMConfig(),
    [],
)
print(answer)
```

This path is particularly relevant because [`AgentAsk.run`](src/rekipedia/orchestrator/agent_ask.py#L275) can call internal tools like `get_symbol`, `get_page`, and `get_relationships`, which are backed by `symbols.json`, wiki markdown, and [`SqliteStore`](src/rekipedia/orchestrator/agent_ask.py#L141).

### CLI + API combined pattern

Even though the CLI parser is not available in the analysis snapshot, the likely operational pattern is:

```bash
rekipedia <scan-or-build-command>
```

followed by Python integration against the resulting `.rekipedia` directory:

```python
from rekipedia.orchestrator.run_ask import stream_ask
from rekipedia.models.contracts import LLMConfig

for token in stream_ask(
    "Summarize the current repository architecture.",
    "/path/to/repo",
    "/path/to/repo/.rekipedia",
    LLMConfig(),
    [],
):
    print(token, end="")
```

This pattern is consistent with the tests and with the internal use of `output_dir` throughout the ask/planning APIs.

> **Sources:** `src/rekipedia/orchestrator/run_ask.py` · `src/rekipedia/orchestrator/agent_ask.py` · `src/rekipedia/synthesis/planner.py` · `src/rekipedia/synthesis/agent_planner.py` · [`tests/test_agent_ask.py`](tests/test_agent_ask.py)

## Notes on Coverage and Gaps

The provided analysis snapshot contains strong evidence for the ask and planning APIs, but it does not include the actual `rekipedia.cli` module. Therefore, no verified list of CLI subcommands, flags, or positional arguments can be given without speculation. If you need CLI documentation with full option tables, the next step should be to inspect `src/rekipedia/cli.py` or the package’s console entry module directly.

The most important tested integration behavior is the agentic ask fallback controlled by `REKIPEDIA_AGENT_ASK=1` and the planner’s fallback behavior when the LLM fails. The tests in [`tests/test_agent_ask.py`](tests/test_agent_ask.py#L60) demonstrate that the system is designed to stay usable even when indexes are missing or external model calls fail.

> **Sources:** `tests/test_agent_ask.py` · `src/rekipedia/orchestrator/run_ask.py` · `src/rekipedia/orchestrator/agent_ask.py` · `src/rekipedia/synthesis/planner.py` · `src/rekipedia/synthesis/agent_planner.py`