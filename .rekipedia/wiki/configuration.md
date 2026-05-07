---
slug: configuration
title: "Configuration Reference"
section: general
pin: false
importance: 50
created_at: 2026-05-07T04:12:19Z
rekipedia_version: 0.10.9
---

# Configuration Reference

## Configuration Files

Based on the repository analysis, there are only two files that appear to be configuration-bearing in the top level set:

| File | Purpose | Notes |
|------|---------|-------|
| [`package.json`](package.json) | Node/package metadata and JavaScript ecosystem configuration | Listed as `config` in the analysis data. No config-key inventory was provided in the symbol data, so the specific settings cannot be enumerated from the static analysis alone. |
| [`pyproject.toml`](pyproject.toml) | Python project metadata and tooling configuration | Listed as `config` in the analysis data. The analysis payload does not include the TOML contents or symbols, so the exact options are not observable here. |

### What is and is not visible

The repository scan did **not** surface any explicit YAML, JSON, `.env`, or TOML application-specific runtime configuration files beyond `pyproject.toml` and `package.json`. No `config.yaml`, `settings.toml`, `.env`, or similar files were present in `files_seen`.

The practical implication is that the runtime configuration for the application is likely defined in code, via CLI parameters, or through environment-variable inspection, rather than through a dedicated config file. That matches the observed CLI and runtime modules such as [`rekipedia.cli.embed`](src/rekipedia/cli/embed.py), [`rekipedia.cli.note`](src/rekipedia/cli/note.py), [`run_digest`](src/rekipedia/orchestrator/run_digest.py), [`run_update`](src/rekipedia/orchestrator/run_update.py), and [`create_app`](src/rekipedia/server/app.py#L21).

> **Sources:** `package.json` · `pyproject.toml` · `src/rekipedia/cli/embed.py` · `src/rekipedia/cli/note.py` · `src/rekipedia/orchestrator/run_digest.py` · `src/rekipedia/orchestrator/run_update.py` · `src/rekipedia/server/app.py#L21-L663`

## Configuration Reference

Because the analysis data does not expose the contents of `package.json` or `pyproject.toml`, a key-by-key configuration table cannot be reconstructed faithfully without inventing values. The repository snapshot only proves that these files exist and are treated as configuration files.

### `package.json`

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| _Not observable from analysis_ | — | — | — | The file exists and is classified as configuration, but its contents were not included in the analysis payload. |

### `pyproject.toml`

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| _Not observable from analysis_ | — | — | — | The file exists and is classified as configuration, but its contents were not included in the analysis payload. |

### Runtime configuration inferred from code

Although file-based settings are not visible, the codebase clearly consumes runtime configuration objects and parameters:

- [`embed_cmd(repo_path, output_dir, model, provider, api_key, base_url, top_k, verbose)`](src/rekipedia/cli/embed.py#L85-L201) accepts explicit CLI parameters for RAG embedding.
- [`run_ask(question, repo_root, output_dir, llm_config, history)`](src/rekipedia/orchestrator/run_ask.py#L304-L330) accepts an [`LLMConfig`](src/rekipedia/orchestrator/run_ask.py) object and conversation history.
- [`run_digest(repo_root, output_dir, llm_config)`](src/rekipedia/orchestrator/run_digest.py#L45-L433) and [`run_update(repo_root, output_dir, llm_config)`](src/rekipedia/orchestrator/run_update.py#L27-L244) both take an [`LLMConfig`](src/rekipedia/orchestrator/run_digest.py) runtime object.
- [`create_app(repo_root, output_dir, llm_config)`](src/rekipedia/server/app.py#L21-L663) uses the same pattern for server startup.

This suggests that configuration is primarily injected through arguments and objects rather than loaded from a persistent settings file.

> **Sources:** `src/rekipedia/cli/embed.py#L85-L201` · [`embed_cmd`](src/rekipedia/cli/embed.py#L85-L201) · [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L304-L330) · [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45-L433) · [`run_update`](src/rekipedia/orchestrator/run_update.py#L27-L244) · [`create_app`](src/rekipedia/server/app.py#L21-L663)

## Configuration Examples

Because the file contents are not available, I can only provide **shape-level examples** that reflect the observed runtime model, not exact repository values.

### Minimal runtime configuration example

This is the minimal shape implied by the API surface for the main flows:

```python
from pathlib import Path

repo_root = Path(".")
output_dir = Path(".rekipedia")
llm_config = {
    "model": "default-model",
}
```

### Full-featured runtime configuration example

The embedding CLI and orchestration functions indicate a broader configuration surface:

```python
from pathlib import Path

config = {
    "repo_root": Path("/path/to/repo"),
    "output_dir": Path("/path/to/repo/.rekipedia"),
    "llm_config": {
        "model": "llama4",
        "provider": "ollama",
        "api_key": None,
        "base_url": None,
    },
    "embed": {
        "top_k": 10,
        "verbose": False,
    },
    "notes": {
        "tag": "tech-lead",
    },
}
```

These examples are intentionally generic: the analysis confirms the existence of these inputs, but not the exact field names inside `LLMConfig` or any hidden file format.

> **Sources:** [`embed_cmd`](src/rekipedia/cli/embed.py#L85-L201) · [`run_ask`](src/rekipedia/orchestrator/run_ask.py#L304-L330) · [`run_digest`](src/rekipedia/orchestrator/run_digest.py#L45-L433) · [`run_update`](src/rekipedia/orchestrator/run_update.py#L27-L244) · [`create_app`](src/rekipedia/server/app.py#L21-L663)

## Runtime Configuration

### CLI flags and command parameters

The clearest runtime overrides in the codebase are the CLI arguments accepted by [`embed_cmd`](src/rekipedia/cli/embed.py#L85-L201):

| Parameter | Role |
|-----------|------|
| `repo_path` | Repository to index |
| `output_dir` | Output location for `.rekipedia/` artifacts |
| `model` | Embedding model name |
| `provider` | Model provider name |
| `api_key` | API key for the embedding backend |
| `base_url` | Custom LiteLLM/OpenAI-compatible endpoint |
| `top_k` | Number of nearest results to retrieve |
| `verbose` | Enables verbose logging |

The notes CLI also exposes runtime behavior through command parameters, as seen in [`note_add`](src/rekipedia/cli/note.py#L35-L42), [`note_list`](src/rekipedia/cli/note.py#L49-L64), [`note_remove`](src/rekipedia/cli/note.py#L70-L89), [`note_edit`](src/rekipedia/cli/note.py#L96-L120), and [`note_import`](src/rekipedia/cli/note.py#L127-L153). These command options control filtering, JSON output, edit behavior, file import, and dry-run semantics.

### Environment-variable overrides

The analysis data confirms at least one explicit env-var override in the RAG layer:

- [`EmbedPipeline.search`](src/rekipedia/rag/embedder.py#L610-L711) documents `REKIPEDIA_RAG_MMR=0` to disable Maximal Marginal Relevance diversification.

The payload also shows imports of `os` in several modules, including [`rekipedia.cli.embed`](src/rekipedia/cli/embed.py), [`rekipedia.cli.note`](src/rekipedia/cli/note.py), [`rekipedia.orchestrator.run_ask`](src/rekipedia/orchestrator/run_ask.py), and [`rekipedia.rag.embedder`](src/rekipedia/rag/embedder.py), which strongly suggests additional environment-variable usage may exist, but the actual env-var names are not observable from the provided data.

### File-based config vs runtime override precedence

What can be stated with confidence is:

1. CLI parameters are accepted directly by the main entry points.
2. Runtime objects such as `LLMConfig` are passed into orchestration and server layers.
3. At least one env var (`REKIPEDIA_RAG_MMR`) overrides a default behavior in the embedding search path.

What cannot be stated from the current analysis is the exact precedence order for `package.json` or `pyproject.toml` settings, because their contents are not available.

> **Sources:** [`embed_cmd`](src/rekipedia/cli/embed.py#L85-L201) · [`note_add`](src/rekipedia/cli/note.py#L35-L42) · [`note_list`](src/rekipedia/cli/note.py#L49-L64) · [`note_remove`](src/rekipedia/cli/note.py#L70-L89) · [`note_edit`](src/rekipedia/cli/note.py#L96-L120) · [`note_import`](src/rekipedia/cli/note.py#L127-L153) · [`EmbedPipeline.search`](src/rekipedia/rag/embedder.py#L610-L711)

## Validation

### What is observable

No dedicated Pydantic model, JSON schema, or TOML/YAML schema validator is visible in the analysis payload for configuration files. There is also no direct evidence of a `Settings` class, `BaseSettings`, or a file-backed config loader.

Instead, validation appears to happen in three ways:

1. **Typed runtime objects**  
   The orchestration layer uses [`LLMConfig`](src/rekipedia/orchestrator/run_ask.py), which implies structured validation via the config object itself, even though the class definition is not present in the payload.

2. **CLI argument validation**  
   The Click-based commands in [`rekipedia.cli.embed`](src/rekipedia/cli/embed.py) and [`rekipedia.cli.note`](src/rekipedia/cli/note.py) enforce types and required/optional argument handling at the command boundary.

3. **Operational checks / graceful fallback**  
   - [`_check_rag_deps()`](src/rekipedia/cli/embed.py#L22-L41) validates that `faiss-cpu` and `numpy` are installed before proceeding.
   - [`_verify_scan(output_dir, repo_root)`](src/rekipedia/orchestrator/run_ask.py#L37-L52) validates that a successful scan exists before answering questions.
   - [`SqliteStore._apply_migrations()`](src/rekipedia/storage/sqlite_store.py#L117-L131) validates and advances schema state by applying migration files.
   - [`EmbedPipeline.meta`](src/rekipedia/rag/embedder.py#L717-L724) and [`EmbedPipeline.is_built`](src/rekipedia/rag/embedder.py#L726-L727) validate index state via filesystem presence.

### Practical conclusion

From the evidence available, configuration validation is mostly **implicit and runtime-driven**, rather than driven by a centralized schema file. The strongest candidate for structured validation is the [`LLMConfig`](src/rekipedia/orchestrator/run_ask.py) object, but the exact validation mechanism cannot be confirmed from the current dataset.

> **Sources:** [`_check_rag_deps`](src/rekipedia/cli/embed.py#L22-L41) · [`_verify_scan`](src/rekipedia/orchestrator/run_ask.py#L37-L52) · [`SqliteStore._apply_migrations`](src/rekipedia/storage/sqlite_store.py#L117-L131) · [`EmbedPipeline.meta`](src/rekipedia/rag/embedder.py#L717-L724) · [`EmbedPipeline.is_built`](src/rekipedia/rag/embedder.py#L726-L727)