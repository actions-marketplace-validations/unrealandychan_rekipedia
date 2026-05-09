---
slug: technical-debt
title: "Technical Debt Inventory and Refactoring Assessment"
section: general
pin: false
importance: 50
created_at: 2026-05-09T02:20:24Z
rekipedia_version: 0.12.0
---

# Technical Debt Inventory and Refactoring Assessment

## Summary

This codebase is functionally compact but shows a concentrated cluster of technical debt in its orchestration and planning paths, especially around LLM-driven control flow, prompt assembly, and fallback logic. The overall debt rating is **Medium-High**: the repository appears operational and has meaningful test coverage for one key path, but several core functions are highly coupled, difficult to maintain, and at elevated risk of regression due to large, monolithic implementations.

The most prominent risks are concentrated in [`rekipedia.orchestrator.run_ask`](src/rekipedia/orchestrator/run_ask.py#L1), [`rekipedia.orchestrator.agent_ask`](src/rekipedia/orchestrator/agent_ask.py#L1), and [`rekipedia.synthesis.planner`](src/rekipedia/synthesis/planner.py#L1), where the code relies on many inline heuristics, repeated parsing patterns, and large multi-responsibility functions. Test coverage exists, but it is narrow relative to the implementation surface, with notable gaps around planning fallback behavior and the default plan output model.

> **Sources:** `src/rekipedia/orchestrator/run_ask.py` · `src/rekipedia/orchestrator/agent_ask.py` · `src/rekipedia/synthesis/planner.py` · `tests/test_agent_ask.py`

## Debt Inventory

| # | Area | Severity | Description | Files Affected | Effort to Fix |
|---|------|----------|-------------|----------------|---------------|
| 1 | Query assembly / retrieval orchestration | 🔴 Critical | [`_build_full_system`](src/rekipedia/orchestrator/run_ask.py#L208) combines rewriting, wiki loading, symbol loading, RAG retrieval, page ranking, note scoring, and prompt composition in one large function. | `src/rekipedia/orchestrator/run_ask.py` | XL |
| 2 | Agentic ask control flow | 🔴 Critical | [`AgentAsk.run`](src/rekipedia/orchestrator/agent_ask.py#L275) contains a long ReAct loop with tool dispatch, JSON parsing, fallback handling, and response post-processing in a single method. | `src/rekipedia/orchestrator/agent_ask.py` | L |
| 3 | Planner implementation complexity | 🔴 Critical | [`PlannerAgent.plan`](src/rekipedia/synthesis/planner.py#L186) and [`AgentPlanner.plan`](src/rekipedia/synthesis/agent_planner.py#L155) both implement long branching flows with LLM fallback logic and output normalization. | `src/rekipedia/synthesis/planner.py`, `src/rekipedia/synthesis/agent_planner.py` | L |
| 4 | Heuristic scoring logic | 🟠 High | [`_score_page`](src/rekipedia/orchestrator/run_ask.py#L116) is a dense heuristic scorer with many token-level operations and implicit weighting rules. | `src/rekipedia/orchestrator/run_ask.py` | M |
| 5 | Query rewrite logic | 🟠 High | [`_rewrite_query`](src/rekipedia/orchestrator/run_ask.py#L149) mixes filesystem reads, prompt construction, LLM calls, and parsing of rewritten output. | `src/rekipedia/orchestrator/run_ask.py` | M |
| 6 | Tool handler responsibilities | 🟠 High | [`_ToolHandler`](src/rekipedia/orchestrator/agent_ask.py#L141) bundles symbol lookup, page loading, relationship retrieval, and search tools into one class. | `src/rekipedia/orchestrator/agent_ask.py` | M |
| 7 | Default planning heuristics | 🟠 High | [`_default_plan`](src/rekipedia/synthesis/planner.py#L400) is a large heuristic fallback that mirrors LLM output shape and encodes many assumptions. | `src/rekipedia/synthesis/planner.py` | M |
| 8 | Large summary builder | 🟠 High | [`_build_planning_summary`](src/rekipedia/synthesis/planner.py#L308) has a high out-degree and combines classification, aggregation, and summarization responsibilities. | `src/rekipedia/synthesis/planner.py` | M |
| 9 | Test coverage gaps in planning model | 🟠 High | [`WikiPlan`](src/rekipedia/synthesis/planner.py#L138) and [`_default_plan`](src/rekipedia/synthesis/planner.py#L400) have no direct tests despite being central outputs. | `src/rekipedia/synthesis/planner.py`, `tests/test_agent_ask.py` | S |
| 10 | Repeated “call LLM, parse JSON, fallback” pattern | 🟡 Medium | The same error-tolerant LLM invocation pattern appears in multiple modules, increasing duplication and inconsistency risk. | `src/rekipedia/orchestrator/agent_ask.py`, `src/rekipedia/synthesis/planner.py`, `src/rekipedia/synthesis/agent_planner.py` | M |
| 11 | Broad import surface / coupling | 🟡 Medium | Modules import many internal dependencies, including cross-package links between orchestration and synthesis. | `src/rekipedia/orchestrator/run_ask.py`, `src/rekipedia/orchestrator/agent_ask.py`, `src/rekipedia/synthesis/planner.py`, `src/rekipedia/synthesis/agent_planner.py` | M |
| 12 | Thin test surface | 🟡 Medium | Only one test file exists, which leaves many code paths and edge cases unverified. | `tests/test_agent_ask.py` | M |

> **Sources:** `src/rekipedia/orchestrator/run_ask.py` · `src/rekipedia/orchestrator/agent_ask.py` · `src/rekipedia/synthesis/planner.py` · `src/rekipedia/synthesis/agent_planner.py` · `tests/test_agent_ask.py`

## Critical Issues

### 1) Monolithic prompt assembly and retrieval in `_build_full_system`

[`_build_full_system`](src/rekipedia/orchestrator/run_ask.py#L208) is the most concerning technical debt item in the repository. The function imports and orchestrates wiki page loading, symbol metadata loading, query rewriting, RAG retrieval via [`_rag_chunks`](src/rekipedia/orchestrator/run_ask.py#L86), page ranking via [`_rank_pages_by_query`](src/rekipedia/orchestrator/run_ask.py#L137), note retrieval from `SqliteStore`, and prompt string assembly.

This is a problem because:
- the function is a bridge node with high out-degree and many hidden assumptions,
- failures in any sub-step affect the entire ask flow,
- changes to ranking or retrieval can unintentionally break prompt formatting,
- it is hard to test in isolation due to its broad responsibilities.

A concrete refactor is to split it into smaller composable builders:
- `load_context_sources(...)`
- `rank_context(...)`
- `format_system_prompt(...)`

Example direction:

```python
def load_context_sources(question, output_dir, llm_config):
    rewritten = _rewrite_query(question, output_dir, llm_config)
    pages = _load_wiki_pages(output_dir)
    symbols = _load_symbol_lines(output_dir)
    rag = _rag_chunks(rewritten, output_dir, llm_config, top_k=8)
    return rewritten, pages, symbols, rag

def format_system_prompt(question, rewritten, pages, symbols, rag, notes):
    parts = []
    # assemble incrementally
    return "\n".join(parts)
```

This would preserve behavior while dramatically lowering cognitive load.

> **Sources:** `src/rekipedia/orchestrator/run_ask.py` · L208–L303 · [`_build_full_system`](src/rekipedia/orchestrator/run_ask.py#L208) · [`_rewrite_query`](src/rekipedia/orchestrator/run_ask.py#L149) · [`_load_wiki_pages`](src/rekipedia/orchestrator/run_ask.py#L55) · [`_load_symbol_lines`](src/rekipedia/orchestrator/run_ask.py#L66) · [`_rag_chunks`](src/rekipedia/orchestrator/run_ask.py#L86) · [`_rank_pages_by_query`](src/rekipedia/orchestrator/run_ask.py#L137)

### 2) ReAct loop complexity in `AgentAsk.run`

[`AgentAsk.run`](src/rekipedia/orchestrator/agent_ask.py#L275) implements the agentic conversation loop, tool invocation, message accumulation, fallback-to-single-shot behavior, and final answer extraction. The supporting [`_ToolHandler`](src/rekipedia/orchestrator/agent_ask.py#L141) exposes several tools, and `run` is responsible for coordinating them all.

Why this is problematic:
- the control flow is long and stateful,
- tool call handling and final answer assembly are mixed together,
- there are many branches for direct completion, tool completion, max-iteration fallback, and exception fallback,
- the method depends on brittle JSON model output parsing.

Suggested fix:
- extract a `ToolExecutionLoop` helper,
- separate “decide next action” from “apply tool result”,
- create a small response normalization helper for the various completion types.

> **Sources:** `src/rekipedia/orchestrator/agent_ask.py` · L253–L364 · [`AgentAsk`](src/rekipedia/orchestrator/agent_ask.py#L253) · [`AgentAsk.run`](src/rekipedia/orchestrator/agent_ask.py#L275) · [`_ToolHandler`](src/rekipedia/orchestrator/agent_ask.py#L141)

### 3) Planning fallback and output normalization are overly complex

Both [`PlannerAgent.plan`](src/rekipedia/synthesis/planner.py#L186) and [`AgentPlanner.plan`](src/rekipedia/synthesis/agent_planner.py#L155) implement broad LLM orchestration flows. They rely on a multi-step sequence: building planning summaries, calling the LLM, parsing JSON, normalizing returned pages/sections, and falling back to [`_default_plan`](src/rekipedia/synthesis/planner.py#L400) on failure.

This is a debt hotspot because:
- the fallback path is as complex as the “happy path,”
- the same conceptual work appears twice across two planners,
- normalization code is spread across large functions rather than encapsulated in a model validator.

A better approach is to define a single planning pipeline with:
- summary generation,
- output schema validation,
- normalized page/section construction,
- fallback plan generation.

Potential refactor:

```python
def parse_plan_payload(payload) -> WikiPlan:
    data = json.loads(payload)
    return WikiPlan(data)

def safe_plan(combined, diagrams):
    try:
        payload = llm_call(...)
        return parse_plan_payload(payload)
    except Exception:
        return _default_plan(combined)
```

> **Sources:** `src/rekipedia/synthesis/planner.py` · `src/rekipedia/synthesis/agent_planner.py` · [`PlannerAgent.plan`](src/rekipedia/synthesis/planner.py#L186) · [`AgentPlanner.plan`](src/rekipedia/synthesis/agent_planner.py#L155) · [`_build_planning_summary`](src/rekipedia/synthesis/planner.py#L308) · [`_default_plan`](src/rekipedia/synthesis/planner.py#L400) · [`WikiPlan`](src/rekipedia/synthesis/planner.py#L138)

## Code Smell Patterns

### God-function / multi-responsibility orchestration

Real examples:
- [`_build_full_system`](src/rekipedia/orchestrator/run_ask.py#L208)
- [`AgentAsk.run`](src/rekipedia/orchestrator/agent_ask.py#L275)
- [`PlannerAgent.plan`](src/rekipedia/synthesis/planner.py#L186)
- [`AgentPlanner.plan`](src/rekipedia/synthesis/agent_planner.py#L155)

These functions combine I/O, ranking, prompt building, JSON parsing, and fallback behavior. The result is high coupling and difficult unit testing.

Recommended refactor:
- extract pure helpers for scoring, parsing, and formatting,
- keep top-level methods as orchestration-only wrappers,
- move schema normalization into the data models where possible.

> **Sources:** `src/rekipedia/orchestrator/run_ask.py` · `src/rekipedia/orchestrator/agent_ask.py` · `src/rekipedia/synthesis/planner.py` · `src/rekipedia/synthesis/agent_planner.py`

### Repeated heuristic parsing and ranking logic

Real example:
- [`_extract_keywords`](src/rekipedia/orchestrator/run_ask.py#L104)
- [`_score_page`](src/rekipedia/orchestrator/run_ask.py#L116)
- [`_rank_pages_by_query`](src/rekipedia/orchestrator/run_ask.py#L137)

These functions encode custom scoring with token counts, title boosts, and keyword filtering. The pattern is reasonable, but the scoring logic is tightly packed and likely to drift if expanded.

Recommended refactor:
- define a small scoring strategy object or config dataclass,
- separate lexical extraction from ranking,
- add tests around scoring outcomes rather than implementation details.

> **Sources:** `src/rekipedia/orchestrator/run_ask.py` · L104–L146 · [`_extract_keywords`](src/rekipedia/orchestrator/run_ask.py#L104) · [`_score_page`](src/rekipedia/orchestrator/run_ask.py#L116) · [`_rank_pages_by_query`](src/rekipedia/orchestrator/run_ask.py#L137)

### Tool handler class with too many concerns

[`_ToolHandler`](src/rekipedia/orchestrator/agent_ask.py#L141) exposes `search_code`, `get_symbol`, `get_page`, and `get_relationships`. Each method touches different storage or file-system concerns, and the class also owns tool dispatch.

Recommended refactor:
- split into `SearchTools`, `WikiTools`, and `RelationshipTools`,
- keep dispatching at the orchestrator layer,
- consider a registry mapping tool name to callable to reduce branching.

> **Sources:** `src/rekipedia/orchestrator/agent_ask.py` · L141–L246 · [`_ToolHandler`](src/rekipedia/orchestrator/agent_ask.py#L141) · [`_ToolHandler.dispatch`](src/rekipedia/orchestrator/agent_ask.py#L236)

### Repeated fallback-on-exception pattern

The code repeatedly catches LLM failures and falls back to defaults:
- [`AgentAsk.run`](src/rekipedia/orchestrator/agent_ask.py#L275)
- [`PlannerAgent.plan`](src/rekipedia/synthesis/planner.py#L186)
- [`AgentPlanner.plan`](src/rekipedia/synthesis/agent_planner.py#L155)
- [`_rewrite_query`](src/rekipedia/orchestrator/run_ask.py#L149)

This is robust, but the implementation is repetitive and easy to get inconsistent.

Recommended refactor:
- centralize LLM call wrappers with shared retry/fallback policy,
- standardize telemetry/logging for failures.

> **Sources:** `src/rekipedia/orchestrator/agent_ask.py` · `src/rekipedia/orchestrator/run_ask.py` · `src/rekipedia/synthesis/planner.py` · `src/rekipedia/synthesis/agent_planner.py`

## Missing Tests

Test coverage is limited relative to the implementation footprint. The analysis indicates **5 implementation files** and **1 test file**, which is a thin ratio for the number of control-flow-heavy functions present.

Specific under-tested areas:
- [`_default_plan`](src/rekipedia/synthesis/planner.py#L400) — explicitly identified as called multiple times with no test coverage.
- [`WikiPlan`](src/rekipedia/synthesis/planner.py#L138) — central output type, but not directly tested.
- [`_rewrite_query`](src/rekipedia/orchestrator/run_ask.py#L149) — no dedicated tests visible.
- [`_score_page`](src/rekipedia/orchestrator/run_ask.py#L116) and [`_rank_pages_by_query`](src/rekipedia/orchestrator/run_ask.py#L137) — heuristic logic is unverified.
- [`_build_full_system`](src/rekipedia/orchestrator/run_ask.py#L208) — high-risk prompt builder with no direct tests.
- [`PlannerAgent.plan`](src/rekipedia/synthesis/planner.py#L186) and [`AgentPlanner.plan`](src/rekipedia/synthesis/agent_planner.py#L155) — happy path and fallback path are partially covered, but normalization edge cases are not.

Current test strengths:
- [`tests/test_agent_ask.py`](tests/test_agent_ask.py#L1) covers tool handler behavior and basic agent/planner flows.
- There is direct coverage for agent fallback and the environment-driven path in [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334).

Recommended additions:
- direct tests for `WikiPlan` construction and lookup methods,
- tests for `_default_plan` with representative `combined` data,
- tests for `_score_page` ranking behavior,
- tests for `_rewrite_query` when rewrite is disabled or malformed.

> **Sources:** `tests/test_agent_ask.py` · `src/rekipedia/synthesis/planner.py` · `src/rekipedia/orchestrator/run_ask.py` · `src/rekipedia/orchestrator/agent_ask.py`

## Dependency & Security Concerns

The available analysis includes `package.json` and `pyproject.toml`, but it does **not** include their dependency contents or version ranges, so no specific outdated package or CVE claim can be made responsibly from the provided evidence alone.

What is observable:
- the project name/version is `rekipedia` `0.13.0`,
- packaging is present for both npm and Python ecosystems,
- build command is `uv build`,
- test command is `pytest`.

Risk notes based on code patterns, not dependency versions:
- heavy use of [`litellm`](src/rekipedia/orchestrator/agent_ask.py#L1) and LLM-driven execution means supply-chain trust and API failure handling are important,
- the code relies on filesystem reads from `.rekipedia/` and JSON parsing from model outputs, which increases robustness requirements,
- if dependency auditing is not already in CI, it should be added.

Recommended next step:
- inspect `package.json` and `pyproject.toml` directly for pinned versions, then run the dependency audit toolchain appropriate to each ecosystem.

> **Sources:** `package.json` · `pyproject.toml` · `src/rekipedia/orchestrator/agent_ask.py` · `src/rekipedia/orchestrator/run_ask.py` · `src/rekipedia/synthesis/planner.py`

## TODO / FIXME Tracker

No TODO, FIXME, HACK, or XXX comments were provided in the analysis data, so no tracker entries can be reported with confidence.

| File | Line | Comment | Suggested Action |
|------|------|---------|------------------|
| — | — | No comments evidenced in provided analysis | Run a repository-wide search for `TODO|FIXME|HACK|XXX` to verify |

> **Sources:** `README.md` · `RELEASE-NOTES.md` · `package.json` · `pyproject.toml` · `src/rekipedia/__init__.py` · `src/rekipedia/orchestrator/agent_ask.py` · `src/rekipedia/orchestrator/run_ask.py` · `src/rekipedia/synthesis/agent_planner.py` · `src/rekipedia/synthesis/planner.py` · `tests/test_agent_ask.py`

## Refactoring Roadmap

| Priority | Action | Rationale | Estimated Effort |
|----------|--------|-----------|------------------|
| 1 | Split [`_build_full_system`](src/rekipedia/orchestrator/run_ask.py#L208) into smaller pure helpers | Highest coupling and widest blast radius; easiest source of regressions | XL |
| 2 | Extract a reusable LLM fallback wrapper for ask/planner/query-rewrite flows | Reduces duplicated error handling and makes failure behavior consistent | M |
| 3 | Decompose [`AgentAsk.run`](src/rekipedia/orchestrator/agent_ask.py#L275) into loop, dispatch, and finalization helpers | Improves testability and makes tool-call handling easier to reason about | L |
| 4 | Normalize planner output handling around [`WikiPlan`](src/rekipedia/synthesis/planner.py#L138) | Stabilizes core output shape and reduces parser brittleness | M |
| 5 | Add direct unit tests for `_default_plan`, `WikiPlan`, `_score_page`, and `_rewrite_query` | Closes the most important coverage gaps with high value and low effort | S |
| 6 | Split [`_ToolHandler`](src/rekipedia/orchestrator/agent_ask.py#L141) into domain-specific tool classes | Reduces class size and isolates filesystem vs storage responsibilities | M |
| 7 | Replace ad hoc ranking heuristics with a configurable scoring strategy | Makes relevance tuning safer and more transparent | M |

> **Sources:** `src/rekipedia/orchestrator/run_ask.py` · `src/rekipedia/orchestrator/agent_ask.py` · `src/rekipedia/synthesis/planner.py` · `src/rekipedia/synthesis/agent_planner.py` · `tests/test_agent_ask.py`

## Closing Assessment

The codebase is not in a state of immediate architectural failure, but its core ask/planning path has accumulated enough structural complexity that future feature work will become increasingly expensive unless it is paid down. The best ROI comes from extracting pure functions and shared wrappers around prompt assembly, LLM invocation, and fallback behavior, then expanding tests around the stable data models and heuristics.

> **Sources:** `src/rekipedia/orchestrator/run_ask.py` · `src/rekipedia/orchestrator/agent_ask.py` · `src/rekipedia/synthesis/planner.py` · `src/rekipedia/synthesis/agent_planner.py`