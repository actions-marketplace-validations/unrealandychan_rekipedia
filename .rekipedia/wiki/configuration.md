---
slug: configuration
title: "Configuration Surfaces and Defaults"
section: getting-started
tags: [getting-started, configuration]
pin: false
importance: 66
created_at: 2026-05-05T04:57:59Z
rekipedia_version: 0.10.3
---

# Configuration Surfaces and Defaults

This page documents the user-facing configuration surfaces that are observable in the repository: repository-local config files, environment variables, CLI flags that interact with config, and schema/sample files. It intentionally excludes CI workflow settings and developer-only cache artifacts.

## Configuration Files Overview

The repository uses a small number of explicit configuration files, plus a few runtime-adjacent manifest formats that influence behavior. The table below focuses on files that a user might reasonably edit to change how the tool runs.

| File | Format | What it controls | Notes |
|------|--------|------------------|-------|
| [`.env.sample`](.env.sample) | Shell-style env file | Example runtime environment variables | Sample only; useful for local setup and discovering supported env vars |
| [`go/.goreleaser.yaml`](go/.goreleaser.yaml) | YAML | Release packaging/publishing for the Go build | Not runtime behavior, but user-facing for maintainers |
| [`pyproject.toml`](pyproject.toml) | TOML | Python package metadata and tooling config | Also implies the Python entry point and project name/version |
| [`package.json`](package.json) | JSON | Node package metadata and scripts | Relevant for the JS wrapper/CLI entry point |
| [`tests/fixtures/mini-py-repo/pyproject.toml`](tests/fixtures/mini-py-repo/pyproject.toml) | TOML | Sample project metadata used by tests | Demonstrates how the extractor sees Python config files |
| [`tests/fixtures/mini-ts-repo/package.json`](tests/fixtures/mini-ts-repo/package.json) | JSON | Sample project metadata used by tests | Demonstrates how the extractor sees TypeScript/Node config files |
| [`tests/fixtures/mini-ts-repo/tsconfig.json`](tests/fixtures/mini-ts-repo/tsconfig.json) | JSON | TypeScript project configuration | Used as a parsing/extraction fixture |
| [`tests/fixtures/mini-py-repo/.close-wiki/config.yml`](tests/fixtures/mini-py-repo/.close-wiki/config.yml) | YAML | Sample repo-local tool config | This is the clearest example of a user-editable project config file |
| [`schemas/analysis_result.schema.json`](schemas/analysis_result.schema.json) | JSON Schema | Shape of analysis export payloads | A schema file, not a runtime config, but important for output consumers |

### What is *not* included

This page does not cover editor/formatter/linter configs such as `.editorconfig`, `.eslintrc.json`, `.prettierrc.json`, `.golangci.yml`, or `.ruff_cache`. Those are developer workflow settings or caches rather than end-user runtime configuration.

> **Sources:** `tests/fixtures/mini-py-repo/.close-wiki/config.yml` · `tests/fixtures/mini-py-repo/pyproject.toml` · `tests/fixtures/mini-ts-repo/package.json` · `tests/fixtures/mini-ts-repo/tsconfig.json` · `pyproject.toml` · `package.json` · `schemas/analysis_result.schema.json`

## Runtime Configuration Model

At runtime, the Go implementation centers around the [`LLMConfig`](go/internal/models/contracts.go#L6-L15) type and its default constructor [`DefaultLLMConfig`](go/internal/models/contracts.go#L18-L23). Tests explicitly verify the default config path via [`TestDefaultLLMConfig`](go/internal/models/contracts_test.go#L5-L13) and CLI loading behavior via [`loadLLMConfig`](go/cmd/rekipedia/cmd/scan.go#L143-L161).

The default shape implied by code/tests is:

- a model name is present by default
- provider/base URL inference exists for OpenAI-style and compatible endpoints
- the CLI can load configuration and fall back to defaults when no explicit env overrides are present

A practical runtime config example, based on the contract and loader behavior, looks like this:

```yaml
llm:
  model: gpt-4.1-mini
  base_url: https://api.openai.com/v1
  api_key: ${OPENAI_API_KEY}
```

The exact on-disk format for this config is not fully exposed in the analysis data, but the code clearly uses structured fields in [`LLMConfig`](go/internal/models/contracts.go#L6-L15) rather than an untyped map. The tests show that defaults are safe to use even when the user supplies little or no explicit configuration.

### Default values inferred from code and tests

| Setting | Inferred default | Evidence |
|---------|------------------|----------|
| LLM model | non-empty default model | [`DefaultLLMConfig`](go/internal/models/contracts.go#L18-L23), [`TestDefaultLLMConfig`](go/internal/models/contracts_test.go#L5-L13) |
| Base URL | inferred from provider/model when missing | [`inferBaseURL`](go/internal/llm/client.go#L148-L157), [`inferBaseURLForProvider`](go/internal/llm/client.go#L376-L385), [`TestInferBaseURL`](go/internal/llm/client_test.go#L120-L136) |
| System prompt inclusion | included only when provided | [`buildMessages`](go/internal/llm/client.go#L344-L355), [`TestBuildMessagesWithSystem`](go/internal/llm/client_test.go#L274-L285) |
| No explicit config | loader returns defaults | [`loadLLMConfig`](go/cmd/rekipedia/cmd/scan.go#L143-L161), [`TestLoadLLMConfigDefaults`](go/cmd/rekipedia/cmd/root_test.go#L104-L110) |

> **Sources:** [`LLMConfig`](go/internal/models/contracts.go#L6-L15) · [`DefaultLLMConfig`](go/internal/models/contracts.go#L18-L23) · [`loadLLMConfig`](go/cmd/rekipedia/cmd/scan.go#L143-L161) · [`TestDefaultLLMConfig`](go/internal/models/contracts_test.go#L5-L13) · [`TestLoadLLMConfig`](go/cmd/rekipedia/cmd/root_test.go#L91-L102) · [`TestLoadLLMConfigDefaults`](go/cmd/rekipedia/cmd/root_test.go#L104-L110)

## Environment Variables

The clearest environment-variable surface visible in the repository is the sample file [` .env.sample`](.env.sample). Although the analysis payload does not enumerate the file contents line-by-line, its presence strongly indicates that the project supports environment-based local configuration, especially for credentials and provider endpoints.

The supporting code also suggests the following runtime concerns are env-driven:

- LLM provider authentication
- provider selection / base URL inference
- possibly local server or storage paths, although those are not explicitly surfaced in the indexed symbols

The LLM client is constructed around [`Client`](go/internal/llm/client.go#L110-L115) and uses provider inference helpers like [`providerFromModel`](go/internal/llm/client.go#L369-L374) and [`inferBaseURLForProvider`](go/internal/llm/client.go#L376-L385). This makes environment variables the natural way to supply secrets or override endpoints without editing a config file.

### Likely user-facing env-var categories

| Category | Purpose | Evidence |
|----------|---------|----------|
| API credentials | authenticate requests to the LLM provider | `LLMConfig`, `Client`, `.env.sample` |
| Base URL override | direct requests to an OpenAI-compatible server | [`inferBaseURL`](go/internal/llm/client.go#L148-L157) |
| Model selection | choose the chat/completions model | [`LLMConfig`](go/internal/models/contracts.go#L6-L15) |

Because the sample file is not expanded in the provided analysis data, the exact variable names should be read from [` .env.sample`](.env.sample) itself.

> **Sources:** [`.env.sample`](.env.sample) · [`Client`](go/internal/llm/client.go#L110-L115) · [`inferBaseURL`](go/internal/llm/client.go#L148-L157) · [`providerFromModel`](go/internal/llm/client.go#L369-L374) · [`inferBaseURLForProvider`](go/internal/llm/client.go#L376-L385)

## CLI Configuration and Precedence

The repository has a CLI surface defined under [`go/cmd/rekipedia/cmd`](go/cmd/rekipedia/cmd/root.go#L36-L48) and mirrored in Python entry points. The primary runtime commands that interact with config are:

- [`scan`](go/cmd/rekipedia/cmd/scan.go)
- [`serve`](go/cmd/rekipedia/cmd/serve.go#L29-L51)
- [`ask`](go/cmd/rekipedia/cmd/ask.go#L87-L174)
- [`update`](go/cmd/rekipedia/cmd/update.go)
- [`watch`](go/cmd/rekipedia/cmd/watch.go#L14-L35)

The tests show that config defaults are loadable through CLI-adjacent helpers and that flags are registered on individual subcommands. For example, [`TestEmbedCmdFlags`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L30-L37), [`TestExportCmdFlags`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L62-L69), and [`TestUpdateCmdFlags`](go/cmd/rekipedia/cmd/embed_export_update_test.go#L98-L105) confirm that user-facing commands expose additional tuning flags.

### Observed precedence model

The explicit precedence order is not fully codified in a single symbol, but the code strongly suggests the standard pattern:

1. CLI flags win when a command exposes them
2. Environment variables provide runtime overrides and secrets
3. Config-file/default values fill in the rest

This is supported by the presence of a loader function [`loadLLMConfig`](go/cmd/rekipedia/cmd/scan.go#L143-L161), the model defaults in [`DefaultLLMConfig`](go/internal/models/contracts.go#L18-L23), and provider inference in the LLM client.

### Practical precedence example

If a user launches the CLI with a model flag, that should override any config file value. If no flag is supplied, the loader consults environment-derived state. If neither is present, the app falls back to [`DefaultLLMConfig`](go/internal/models/contracts.go#L18-L23).

```bash
# Highest precedence: explicit CLI selection
reki scan --model gpt-4.1-mini

# Next: environment-based configuration
export OPENAI_API_KEY=...
reki scan

# Fallback: code defaults
reki scan
```

> **Sources:** [`Execute`](go/cmd/rekipedia/cmd/root.go#L44-L48) · [`loadLLMConfig`](go/cmd/rekipedia/cmd/scan.go#L143-L161) · [`DefaultLLMConfig`](go/internal/models/contracts.go#L18-L23) · [`TestRootCommandHasSubcommands`](go/cmd/rekipedia/cmd/root_test.go#L19-L29) · [`TestLoadLLMConfig`](go/cmd/rekipedia/cmd/root_test.go#L91-L102)

## Sample and Schema Files

### `.env.sample`

[` .env.sample`](.env.sample) is the main onboarding aid for environment-based configuration. Users should treat it as the authoritative template for required secrets and optional overrides.

### `tests/fixtures/mini-py-repo/.close-wiki/config.yml`

[`tests/fixtures/mini-py-repo/.close-wiki/config.yml`](tests/fixtures/mini-py-repo/.close-wiki/config.yml) is a representative project-local configuration file. It demonstrates that the tool can consume repo-scoped YAML config, which is the kind of file most users would add or edit in a target repository.

### `schemas/analysis_result.schema.json`

[`schemas/analysis_result.schema.json`](schemas/analysis_result.schema.json) defines the JSON schema for analysis output. This is not a runtime control file, but it is relevant for integrations, downstream processors, and validating exported results.

### Language-specific fixture configs

The extractor test suite proves that config files in the target repo are first-class inputs for analysis:

- [`TestConfigPackageJSON`](go/internal/extractor/extractor_test.go#L296-L332)
- [`TestConfigPyprojectToml`](go/internal/extractor/extractor_test.go#L334-L356)
- [`TestConfigDockerfile`](go/internal/extractor/extractor_test.go#L358-L376)
- [`TestConfigGoMod`](go/internal/extractor/extractor_test.go#L378-L401)
- [`TestConfigMakefile`](go/internal/extractor/extractor_test.go#L403-L426)

These tests indicate the supported config surface is intentionally broad: repository metadata and build files are scanned and can influence the generated wiki, graph, and RAG content.

> **Sources:** [`TestConfigPackageJSON`](go/internal/extractor/extractor_test.go#L296-L332) · [`TestConfigPyprojectToml`](go/internal/extractor/extractor_test.go#L334-L356) · [`TestConfigDockerfile`](go/internal/extractor/extractor_test.go#L358-L376) · [`TestConfigGoMod`](go/internal/extractor/extractor_test.go#L378-L401) · [`TestConfigMakefile`](go/internal/extractor/extractor_test.go#L403-L426) · [`schemas/analysis_result.schema.json`](schemas/analysis_result.schema.json)

## Main Runtime Configuration Example

A user running the tool locally will typically need to configure an LLM provider and optionally adjust how the CLI resolves defaults. Based on the code paths around [`RunAsk`](go/internal/orchestrator/run_ask.go#L59-L109), [`RunUpdate`](go/internal/orchestrator/run_update.go#L30-L179), and [`RunDigest`](go/internal/orchestrator/run_digest.go#L48-L309), a minimal working configuration is conceptually:

```env
# Example only; see .env.sample for the exact variable names
OPENAI_API_KEY=...
REKIPEDIA_MODEL=gpt-4.1-mini
REKIPEDIA_BASE_URL=https://api.openai.com/v1
```

In practice, the CLI may also work with an OpenAI-compatible local endpoint, since the client has dedicated inference helpers for provider-specific base URLs.

### Safe defaults

The codebase is designed so that the tool can start with limited user input:

- default model values are supplied by [`DefaultLLMConfig`](go/internal/models/contracts.go#L18-L23)
- base URL can be inferred via [`inferBaseURL`](go/internal/llm/client.go#L148-L157)
- CLI commands are registered under the root command with sensible subcommand structure

That means the main configuration burden for end users is usually just credentials and provider choice, not a large bespoke config file.

> **Sources:** [`RunAsk`](go/internal/orchestrator/run_ask.go#L59-L109) · [`RunUpdate`](go/internal/orchestrator/run_update.go#L30-L179) · [`RunDigest`](go/internal/orchestrator/run_digest.go#L48-L309) · [`inferBaseURL`](go/internal/llm/client.go#L148-L157) · [`DefaultLLMConfig`](go/internal/models/contracts.go#L18-L23)

## Notes on Unsupported or Internal-Only Settings

Some configuration-looking files in the repository are not part of the user-facing runtime surface and should generally be ignored for this page:

- CI and release workflow files under [`.github/workflows`](.github/workflows)
- lint/pre-commit/editor settings at the repository root
- cache directories such as [`.ruff_cache`](.ruff_cache)

The implementation also contains several internal constants, helper functions, and storage defaults that are user-visible only indirectly. For example, [`DefaultPath`](go/internal/storage/store.go#L38-L40) and [`Open`](go/internal/storage/store.go#L24-L35) determine where the SQLite store lives, but the analysis data does not expose a user-editable config file for that path.

> **Sources:** [`Open`](go/internal/storage/store.go#L24-L35) · [`DefaultPath`](go/internal/storage/store.go#L38-L40) · [`Store`](go/internal/storage/store.go#L18-L21)