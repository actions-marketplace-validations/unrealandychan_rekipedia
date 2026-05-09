---
slug: configuration
title: "Configuration Reference"
section: general
pin: false
importance: 50
created_at: 2026-05-09T02:23:19Z
rekipedia_version: 0.12.0
---

# Configuration Reference

## Overview

This repository’s observable configuration surface is relatively small and is split across **package metadata**, **runtime environment variables**, and **test scaffolding**. Based on the analysis data, there are no dedicated YAML, TOML, JSON, or `.env` application config files beyond the project metadata files [`package.json`](package.json) and [`pyproject.toml`](pyproject.toml). The code paths in [`rekipedia.orchestrator.run_ask`](src/rekipedia/orchestrator/run_ask.py#L1) and [`rekipedia.orchestrator.agent_ask`](src/rekipedia/orchestrator/agent_ask.py#L1) also read environment variables directly, most notably `REKIPEDIA_AGENT_ASK`.

The configuration model is therefore “hybrid”:
- **Static project/package config** for build/runtime packaging
- **Programmatic configuration objects** such as `LLMConfig` passed into orchestration functions
- **Environment overrides** for toggling agentic ask mode

Because the actual contents of `pyproject.toml` and `package.json` were not included in the analysis payload, this page documents only what is directly evidenced by code and metadata relationships, and explicitly marks gaps where the values are not observable.

---

## Configuration Files

| File | Format | Purpose |
|------|--------|---------|
| [`pyproject.toml`](pyproject.toml) | TOML | Python package/build configuration. The analysis confirms it exists and that the build command is `uv build`, but the detailed keys are not visible in the payload. |
| [`package.json`](package.json) | JSON | Node/npm package metadata. The analysis shows package identity metadata: `rekipedia` version `0.13.0`. |
| [`README.md`](README.md) | Markdown | Documentation, likely describing usage and configuration, but not a machine-readable config file. Included here only because it may contain user-facing setup guidance. |
| [`RELEASE-NOTES.md`](RELEASE-NOTES.md) | Markdown | Release history; not runtime configuration. |
| Environment variables | N/A | Runtime overrides, most importantly `REKIPEDIA_AGENT_ASK`, which changes ask-mode behavior in [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334). |

### Observable file purposes

- [`package.json`](package.json) is the only confirmed non-Python config file with explicit metadata in the analysis payload; the `evidence` block identifies npm package name and version.
- [`pyproject.toml`](pyproject.toml) is the project’s Python build/config file. The build command [`uv build`](#build-and-test-context) implies it participates in packaging, but no concrete keys were exposed.
- No `.env`, YAML, or JSON application config files were present in `files_seen`.

> **Sources:** `package.json` · metadata via `evidence` (`npm_name=rekipedia`, `npm_version=0.13.0`) · [`pyproject.toml`](pyproject.toml) · build command [`uv build`](#build-and-test-context)

---

## Configuration Reference

Because the file contents are not available, this section distinguishes between:
1. **Directly observable configuration keys**
2. **Programmatic runtime parameters**
3. **Unknown file-backed keys** that exist but are not visible in analysis

### `package.json`

The analysis indicates:
- package name: `rekipedia`
- version: `0.13.0`
- entry points: `rekipedia = "rekipedia.cli:main"` and `reki = "rekipedia.cli:main"`

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `name` | string | `rekipedia` | yes | npm package name, captured in analysis evidence. |
| `version` | string | `0.13.0` | yes | Published package version in the analysis evidence. |
| `bin.rekipedia` / `bin.reki` | string | `rekipedia.cli:main` | yes | CLI entry points exposed by the package. |

> **Sources:** `package.json` · package metadata from `evidence` (`npm_name`, `npm_version`, `entry_points`) · [`rekipedia`](package.json) · [`reki`](package.json)

### `pyproject.toml`

The file exists and is part of the repository config surface, but the analysis payload does not include its content. As a result, we can only document what the code/build metadata implies:

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| Unknown (not visible in analysis) | — | — | — | `pyproject.toml` is used for Python packaging/build configuration. The build command `uv build` suggests standard PEP 517/518 metadata is present. |

> **Sources:** `pyproject.toml` · build command `uv build`

### Runtime configuration objects

Several runtime functions accept `llm_config` and other parameters, but these are **not file-backed config keys**. They are still important for operational configuration:

| Key / Parameter | Type | Default | Required | Description |
|-----------------|------|---------|----------|-------------|
| `llm_config` in [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334) | `LLMConfig` | `LLMConfig()` | no | LLM settings passed into the answer flow. |
| `llm_config` in [`stream_ask`](src/rekipedia/orchestrator/run_ask.py#L364) | `LLMConfig` | `LLMConfig()` | no | Same as above, but used for streaming responses. |
| `llm_config` in [`agent_run_ask`](src/rekipedia/orchestrator/agent_ask.py#L371) | `LLMConfig` | `LLMConfig()` | no | Agentic answer mode uses the same configuration object. |
| `llm_config` in [`PlannerAgent`](src/rekipedia/synthesis/planner.py#L180) and [`AgentPlanner`](src/rekipedia/synthesis/agent_planner.py#L144) | `LLMConfig` | caller-provided | yes | Controls planner LLM calls. |

> **Sources:** [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334) · [`stream_ask`](src/rekipedia/orchestrator/run_ask.py#L364) · [`agent_run_ask`](src/rekipedia/orchestrator/agent_ask.py#L371) · [`PlannerAgent`](src/rekipedia/synthesis/planner.py#L180) · [`AgentPlanner`](src/rekipedia/synthesis/agent_planner.py#L144)

---

## Configuration Examples

### Minimal config

Because no explicit application config file schema is visible, the smallest meaningful runtime configuration is the default package metadata plus no environment overrides:

```bash
# No config file required
export REKIPEDIA_AGENT_ASK=0
reki ask "What does the planner do?"
```

This keeps the system on the standard path through [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334) rather than delegating to [`agent_run_ask`](src/rekipedia/orchestrator/agent_ask.py#L371).

### Full-featured config

A “full-featured” configuration, based on what is evidenced in code, would include:
- package installation/entry points from `package.json`
- a normal Python package build via `pyproject.toml`
- explicit LLM settings passed programmatically
- the agentic ask override enabled via environment variable

```bash
export REKIPEDIA_AGENT_ASK=1

python - <<'PY'
from rekipedia.models.contracts import LLMConfig
from rekipedia.orchestrator.run_ask import run_ask

config = LLMConfig()
answer = run_ask(
    question="Trace the answer flow end-to-end.",
    repo_root="/path/to/repo",
    output_dir="/path/to/repo/.rekipedia",
    llm_config=config,
    history=[],
)
print(answer)
PY
```

This setup drives the agentic path into [`agent_run_ask`](src/rekipedia/orchestrator/agent_ask.py#L371) when the environment flag is enabled.

> **Sources:** [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334) · [`agent_run_ask`](src/rekipedia/orchestrator/agent_ask.py#L371) · [`LLMConfig`](src/rekipedia/orchestrator/run_ask.py#L310) · [`package.json`](package.json) · [`pyproject.toml`](pyproject.toml)

---

## Runtime Configuration

The only explicitly evidenced runtime override is:

| Env var | Type | Effect | Observed in |
|---------|------|--------|-------------|
| `REKIPEDIA_AGENT_ASK` | boolean-like string (`"1"`/other) | When set to `1`, [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334) delegates to [`agent_run_ask`](src/rekipedia/orchestrator/agent_ask.py#L371). | [`tests/test_agent_ask.py`](tests/test_agent_ask.py#L283) |

### Behavior details

- In [`test_run_ask_uses_agent_when_env_set`](tests/test_agent_ask.py#L283), the test sets `REKIPEDIA_AGENT_ASK=1` and verifies that `run_ask` routes to the agentic implementation.
- This implies the environment variable acts as a **runtime feature flag** rather than a static configuration value.
- No other env vars are visible in the analysis payload.

### CLI flags

No CLI flag definitions are visible in the analysis data. The repository does expose CLI entry points via `package.json` (`rekipedia` and `reki`), and the package appears to have a CLI main function at `rekipedia.cli:main`, but the actual flag set is not present in the provided files list. Therefore, no concrete flag-to-config mapping can be documented here.

> **Sources:** [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L334) · [`agent_run_ask`](src/rekipedia/orchestrator/agent_ask.py#L371) · [`test_run_ask_uses_agent_when_env_set`](tests/test_agent_ask.py#L283)

---

## Validation

There is no visible Pydantic model or JSON schema for file-based configuration in the provided analysis. Validation is therefore **partially observable** and appears to be handled in two ways:

### 1. Runtime existence checks and guardrails

The code validates the operational environment before executing ask flows:

- [`_verify_scan`](src/rekipedia/orchestrator/run_ask.py#L37) checks that a successful scan exists by consulting [`SqliteStore`](src/rekipedia/storage/sqlite_store.py) and its `get_latest_run_id` method.
- [`AgentAsk.run`](src/rekipedia/orchestrator/agent_ask.py#L275) has fallback behavior when tool-calling is unavailable or the model call fails.
- [`PlannerAgent.plan`](src/rekipedia/synthesis/planner.py#L186) and [`AgentPlanner.plan`](src/rekipedia/synthesis/agent_planner.py#L155) both have fallback paths to `_default_plan` if LLM planning fails.

These are not configuration validators in the strict sense, but they enforce runtime preconditions around configuration use.

### 2. Object-based configuration validation

The repository clearly uses an `LLMConfig` type from [`rekipedia.models.contracts`](src/rekipedia/models/contracts) as the primary configuration object passed into orchestrator and planner functions. However, the analysis payload does not expose the class definition, so we cannot confirm whether it is:
- a Pydantic model
- a dataclass
- a simple typed contract

What is observable is that tests construct it directly via [`_make_config`](tests/test_agent_ask.py#L20), and runtime functions accept it as the canonical settings object.

### What is not observable

- No schema file
- No config validation library import is visible in the analysed files
- No explicit `BaseModel` or `pydantic` symbol is present in the analysis payload

So the safest conclusion is: **configuration validation is mostly implicit and runtime-driven, with `LLMConfig` as the typed boundary, but the exact validation mechanism is not exposed in the current snapshot**.

> **Sources:** [`_verify_scan`](src/rekipedia/orchestrator/run_ask.py#L37) · [`AgentAsk.run`](src/rekipedia/orchestrator/agent_ask.py#L275) · [`PlannerAgent.plan`](src/rekipedia/synthesis/planner.py#L186) · [`AgentPlanner.plan`](src/rekipedia/synthesis/agent_planner.py#L155) · [`LLMConfig`](src/rekipedia/models/contracts) · [`_make_config`](tests/test_agent_ask.py#L20)

---

## Build and Test Context

Although not configuration files themselves, the repository metadata establishes the operational context:

| Command | Purpose |
|---------|---------|
| `uv build` | Build/package the Python project. |
| `pytest` | Run the test suite, including configuration-related behavior such as `REKIPEDIA_AGENT_ASK`. |

These commands suggest the configuration surface is validated primarily through tests rather than schema enforcement.

> **Sources:** build command `uv build` · test command `pytest` · [`tests/test_agent_ask.py`](tests/test_agent_ask.py#L283)

## Gaps and Unknowns

The repository snapshot is missing the contents of the main configuration files, so the following cannot be enumerated precisely:
- exact TOML keys in [`pyproject.toml`](pyproject.toml)
- any npm scripts or additional metadata in [`package.json`](package.json)
- any CLI flags exposed by `rekipedia.cli:main`

If you want, I can produce a second-pass documentation page focused specifically on **runtime/env configuration behavior** once the raw file contents for `pyproject.toml` and `package.json` are available.