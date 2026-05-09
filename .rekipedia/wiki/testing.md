---
slug: testing
title: "Testing Strategy and Test Execution"
section: general
pin: false
importance: 50
created_at: 2026-05-09T02:24:27Z
rekipedia_version: 0.12.0
---

# Testing Strategy and Test Execution

## Testing Philosophy

The testing approach in this repository is intentionally focused on the highest-value behavior: orchestrating LLM-backed workflows, handling tool calls, and preserving safe fallback paths when external services fail. The visible test suite centers on [`tests.test_agent_ask`](tests/test_agent_ask.py#L1), which exercises the orchestration layer in [`rekipedia.orchestrator.agent_ask`](src/rekipedia/orchestrator/agent_ask.py#L1), the query path in [`rekipedia.orchestrator.run_ask`](src/rekipedia/orchestrator/run_ask.py#L1), and the planning layer in [`rekipedia.synthesis.planner`](src/rekipedia/synthesis/planner.py#L1) and [`rekipedia.synthesis.agent_planner`](src/rekipedia/synthesis/agent_planner.py#L1).

The tests are predominantly unit tests with heavy mocking. This is a sensible fit for the codebase because many core paths depend on LLM calls, local file-system state, and a SQLite-backed knowledge store. Instead of relying on live model calls or a fully built repository index, the tests validate deterministic behavior under controlled conditions. For example, the helper mocks [`_mock_direct_response`](tests/test_agent_ask.py#L24) and [`_mock_tool_call_response`](tests/test_agent_ask.py#L35) simulate direct model answers and tool-calling responses respectively, allowing the suite to validate the agent loop in [`AgentAsk.run`](src/rekipedia/orchestrator/agent_ask.py#L275).

There is also a clear emphasis on fallback behavior. Both [`PlannerAgent.plan`](src/rekipedia/synthesis/planner.py#L186) and [`AgentPlanner.plan`](src/rekipedia/synthesis/agent_planner.py#L155) explicitly promise a sensible default when LLM planning fails, and the tests verify that behavior. Likewise, [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334) can delegate to [`agent_run_ask`](src/rekipedia/orchestrator/agent_ask.py#L371) when the agentic mode is enabled, and this delegation is covered by [`test_run_ask_uses_agent_when_env_set`](tests/test_agent_ask.py#L283).

Coverage goals are not stated explicitly in the repository evidence, but the shape of the tests suggests a practical goal: cover all branches that are hard to reproduce manually, especially:
- tool dispatch and lookup behavior in [`_ToolHandler`](src/rekipedia/orchestrator/agent_ask.py#L141),
- direct-answer vs tool-call paths in [`AgentAsk.run`](src/rekipedia/orchestrator/agent_ask.py#L275),
- planner fallback and structured-output handling in [`PlannerAgent.plan`](src/rekipedia/synthesis/planner.py#L186) and [`AgentPlanner.plan`](src/rekipedia/synthesis/agent_planner.py#L155),
- environment-driven switching in [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334).

> **Sources:** `tests/test_agent_ask.py` · L1–L303 · [`tests.test_agent_ask`](tests/test_agent_ask.py#L1) · [`_mock_direct_response`](tests/test_agent_ask.py#L24) · [`_mock_tool_call_response`](tests/test_agent_ask.py#L35) · [`test_agent_ask_direct_answer`](tests/test_agent_ask.py#L112) · [`test_agent_planner_fallback_on_error`](tests/test_agent_ask.py#L263)

## Test Structure

The analysis data shows a very compact test layout: all observed tests live in a single file, [`tests/test_agent_ask.py`](tests/test_agent_ask.py#L1). There are no additional test directories or CI-specific test files in the evidence, so the current structure appears to be:

| Directory / File | Contents | Observed Purpose |
|---|---|---|
| `tests/test_agent_ask.py` | Unit tests, fixtures, helper mocks | Exercise agent tool handling, question answering, planner behavior, and environment-based routing |

Within that file, the tests are organized by behavior rather than by module. The early helpers build reusable test inputs:
- [`_make_config`](tests/test_agent_ask.py#L20) constructs an [`LLMConfig`](tests/test_agent_ask.py#L20) tailored for temporary test directories.
- [`_mock_direct_response`](tests/test_agent_ask.py#L24) returns a mock LLM response without tool calls.
- [`_mock_tool_call_response`](tests/test_agent_ask.py#L35) returns a mock response that requests a single tool invocation.

The test bodies then group naturally into sections:
- tool handler behavior: [`test_tool_handler_search_code_no_index`](tests/test_agent_ask.py#L60), [`test_tool_handler_get_symbol_not_found`](tests/test_agent_ask.py#L67), [`test_tool_handler_get_page_not_found`](tests/test_agent_ask.py#L74), [`test_tool_handler_get_symbol_found`](tests/test_agent_ask.py#L81), [`test_tool_handler_get_page_found`](tests/test_agent_ask.py#L97),
- agent execution modes: [`test_agent_ask_direct_answer`](tests/test_agent_ask.py#L112), [`test_agent_ask_tool_then_finish`](tests/test_agent_ask.py#L133), [`test_agent_ask_finish_tool`](tests/test_agent_ask.py#L155), [`test_agent_ask_max_iterations`](tests/test_agent_ask.py#L173), [`test_agent_ask_fallback_on_error`](tests/test_agent_ask.py#L198),
- planning behavior: [`test_agent_planner_add_pages_and_finalize`](tests/test_agent_ask.py#L220), [`test_agent_planner_fallback_on_error`](tests/test_agent_ask.py#L263),
- runtime routing: [`test_run_ask_uses_agent_when_env_set`](tests/test_agent_ask.py#L283).

This structure suggests a deliberately behavior-driven suite with shared helper functions and no apparent split between unit and integration test directories yet.

> **Sources:** `tests/test_agent_ask.py` · L1–L303 · [`_make_config`](tests/test_agent_ask.py#L20) · [`_mock_direct_response`](tests/test_agent_ask.py#L24) · [`_mock_tool_call_response`](tests/test_agent_ask.py#L35)

## Running Tests

The only test command surfaced in the repository evidence is `pytest` from [`test_commands`](analysis payload). That is the canonical entry point for running the suite.

```bash
# unit tests
pytest

# integration tests
pytest

# with coverage
pytest
```

The evidence does not provide separate unit/integration commands, nor does it show a coverage tool such as `pytest-cov` configured in `pyproject.toml` or `package.json`. So, based on what is visible, the repository currently exposes a single generalized test command rather than a categorized matrix of commands.

If you want to run a single test or a subset, standard `pytest` selection patterns should work, even though they are not explicitly documented in the repository evidence:

```bash
pytest tests/test_agent_ask.py::test_agent_ask_direct_answer
pytest tests/test_agent_ask.py -k "planner"
pytest tests/test_agent_ask.py -k "tool_handler"
```

Because the test file relies heavily on monkeypatching and temporary directories, these invocations should be fast and deterministic. The suite appears designed to avoid requiring a fully built scan or external network access.

> **Sources:** `pyproject.toml` · build/test command evidence inferred from `test_commands` · [`tests/test_agent_ask.py`](tests/test_agent_ask.py#L1)

## Test Categories

### Unit Tests

Most of the observed suite is unit-level and isolates the class or function under test using mocks.

The main units exercised are:

- [`_ToolHandler`](src/rekipedia/orchestrator/agent_ask.py#L141), especially:
  - [`_ToolHandler.search_code`](src/rekipedia/orchestrator/agent_ask.py#L160),
  - [`_ToolHandler.get_symbol`](src/rekipedia/orchestrator/agent_ask.py#L173),
  - [`_ToolHandler.get_page`](src/rekipedia/orchestrator/agent_ask.py#L189),
  - [`_ToolHandler.get_relationships`](src/rekipedia/orchestrator/agent_ask.py#L208),
  - [`_ToolHandler.dispatch`](src/rekipedia/orchestrator/agent_ask.py#L236).
- [`AgentAsk`](src/rekipedia/orchestrator/agent_ask.py#L253), especially [`AgentAsk.run`](src/rekipedia/orchestrator/agent_ask.py#L275).
- [`AgentPlanner`](src/rekipedia/synthesis/agent_planner.py#L144) and [`PlannerAgent`](src/rekipedia/synthesis/planner.py#L180), especially their `plan()` methods.
- [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334) in the environment-switching case.

The key fixture/mocking strategy is visible in the test file:
- [`_make_config`](tests/test_agent_ask.py#L20) builds a minimal [`LLMConfig`](tests/test_agent_ask.py#L20),
- [`_mock_direct_response`](tests/test_agent_ask.py#L24) emulates a normal completion,
- [`_mock_tool_call_response`](tests/test_agent_ask.py#L35) emulates tool-calling behavior,
- `patch` is used throughout to override `litellm` behavior and isolate the agent loop.

This means the suite verifies internal orchestration logic and contract handling without requiring live model tokens or actual RAG index contents.

> **Sources:** `tests/test_agent_ask.py` · L20–L303 · [`_ToolHandler`](tests/test_agent_ask.py#L60) · [`AgentAsk`](tests/test_agent_ask.py#L112) · [`AgentPlanner`](tests/test_agent_ask.py#L220) · [`PlannerAgent`](tests/test_agent_ask.py#L220)

### Integration Tests

No dedicated integration test directory or file is visible in the evidence, so there is no clearly separated integration suite yet. However, some tests do exercise multi-component behavior:
- [`test_agent_ask_tool_then_finish`](tests/test_agent_ask.py#L133) verifies a tool-call round-trip from the mock model through [`AgentAsk.run`](src/rekipedia/orchestrator/agent_ask.py#L275) and back to a final answer.
- [`test_agent_planner_add_pages_and_finalize`](tests/test_agent_ask.py#L220) verifies the planner’s end-to-end use of structured tool calls and finalization into a [`WikiPlan`](src/rekipedia/synthesis/planner.py#L138).
- [`test_run_ask_uses_agent_when_env_set`](tests/test_agent_ask.py#L283) checks that the public [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334) API delegates to the agent path when `REKIPEDIA_AGENT_ASK=1`.

These are “integration-like” in the sense that they cover interactions between functions and modules, but they still use mocks heavily and do not appear to rely on a live SQLite database, real embeddings, or a real model backend.

> **Sources:** `tests/test_agent_ask.py` · L133–L303 · [`AgentAsk.run`](src/rekipedia/orchestrator/agent_ask.py#L275) · [`AgentPlanner.plan`](src/rekipedia/synthesis/agent_planner.py#L155) · [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334)

## Writing New Tests

When adding tests, follow the style already established in [`tests/test_agent_ask.py`](tests/test_agent_ask.py#L1):

### Conventions

- Prefer small helper factories like [`_make_config`](tests/test_agent_ask.py#L20) over repeating setup.
- Mock external boundaries (`litellm`, file content, environment variables) instead of calling real services.
- Keep test names descriptive and behavior-oriented, e.g. `test_agent_ask_fallback_on_error`.
- Use `tmp_path` for filesystem state; several current tests create temporary wiki pages or `symbols.json` files this way.
- Use `monkeypatch`/`patch` to control module behavior and isolate fallback branches.

### Where to Put New Tests

At present, all observed tests are concentrated in `tests/test_agent_ask.py`. If you add coverage for adjacent modules, the existing layout suggests either:
- extending `tests/test_agent_ask.py` for closely related orchestrator/planner behavior, or
- introducing new files under `tests/` organized by area, such as `tests/test_run_ask.py` or `tests/test_planner.py`, if the suite grows.

The repository evidence does not show any enforced test layout policy, so this is a pragmatic recommendation rather than a documented rule.

### Running a Single Test

Use standard pytest node selection:

```bash
pytest tests/test_agent_ask.py::test_agent_ask_direct_answer
pytest tests/test_agent_ask.py::test_agent_planner_fallback_on_error
pytest tests/test_agent_ask.py -k "get_page"
```

If you are working on planner behavior, target the relevant test function directly; for tool behavior, choose the specific `_ToolHandler` case. This keeps iteration fast and ensures that mocking setup stays local to the failing path.

> **Sources:** `tests/test_agent_ask.py` · L20–L303 · [`_make_config`](tests/test_agent_ask.py#L20) · [`test_agent_ask_direct_answer`](tests/test_agent_ask.py#L112) · [`test_agent_planner_add_pages_and_finalize`](tests/test_agent_ask.py#L220)

## CI/CD

No CI configuration files were found in the provided evidence (`ci_files: []`), so there is no observable pipeline to document from the repository snapshot. In other words, there is currently no confirmed GitHub Actions, GitLab CI, or similar workflow file available to describe.

Given the absence of CI evidence, the safest statement is:
- tests are run locally with `pytest`,
- there is no visible automated CI/CD pipeline in the analyzed files.

If CI is added later, a useful pipeline would likely:
1. install dependencies,
2. run `pytest`,
3. optionally run packaging checks such as `uv build` (which is the observed build command).

> **Sources:** `ci_files` empty in analysis data · `test_commands`: `pytest` · `build_commands`: `uv build`