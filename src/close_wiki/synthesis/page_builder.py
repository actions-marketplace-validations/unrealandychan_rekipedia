"""Build wiki pages from combined AnalysisResult using the LLM."""
from __future__ import annotations

import json
import re
from pathlib import Path

from close_wiki.llm.client import LLMClient
from close_wiki.models.contracts import AnalysisResult, LLMConfig

_SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "digest_system.md"

# The 9 canonical pages every project wiki should have
CANONICAL_PAGES = [
    "index",
    "architecture",
    "core-modules",
    "algorithms",
    "cli-and-api",
    "installation-and-setup",
    "configuration",
    "testing",
    "ecosystem-and-integrations",
]

_PAGE_FOCUS: dict[str, str] = {
    "index": """Write a comprehensive project overview page. Include:
## What is this project?
Explain the purpose, goals, and the problem it solves. Reference actual entry points and top-level modules.
## Who is it for?
Target audience and use cases.
## Key Features
Bullet list of the most important capabilities, grounded in the symbols and files found.
## Quick Start
The fastest way to get the project running — use build_commands and entry_points.
## Project Structure
A Mermaid diagram showing the top-level directory/module layout.
## How it Works (High Level)
A 3–5 sentence summary of the end-to-end flow, referencing real symbols.""",

    "architecture": """Write a deep architectural overview. Include:
## System Architecture
If a pre-built module graph is provided in the analysis data under `pre_built_module_graph`, embed it EXACTLY as-is in a mermaid code block — do NOT modify it. Otherwise generate your own `flowchart TD` diagram.
## Component Breakdown
For each major component: what it does, its responsibilities, and which files implement it. For every component, cite the file using inline source links e.g. [`ComponentClass`](path/to/file.py#L1).
## Entry Points
List all entry points from `entry_points` data. For each one: what triggers it, what it does, and inline source link.
## Data Flow
Step-by-step description of how data moves through the system. Use a Mermaid sequence or flowchart diagram.
## Key Design Decisions
Notable patterns used (e.g. plugin architecture, event-driven, pipeline, sandbox isolation). Reference actual code evidence with source citations.
## Inter-Module Dependencies
If a pre-built dependency graph is provided in `pre_built_dependency_graph`, embed it. Otherwise describe the major import relationships.""",

    "core-modules": """Document every significant module/package. For each one:
### Module Name (`path/to/module`)
- **Purpose**: what this module does
- **Public API**: list key exported classes and functions with their signatures
- **Key Classes**: brief description of each class, its constructor, and main methods
- **Key Functions**: signature + one-line description
- **Interactions**: which other modules it imports from / is imported by
Include a Mermaid `classDiagram` showing class hierarchies if applicable.""",

    "algorithms": """Document the core algorithms and data processing logic. Include:
## Overview
What computational problems does this project solve?
## Algorithm Descriptions
For each significant algorithm or processing pipeline found in the symbols:
### Algorithm / Pipeline Name
- **Input**: what data it receives
- **Steps**: numbered list of processing steps
- **Output**: what it produces
- **Complexity**: time/space if discernible from the code
- **Code Reference**: file and function name
## Data Structures
Key data structures (classes, types, schemas) used internally — use a table or class diagram.
## Processing Pipeline
Mermaid flowchart of the main processing pipeline end-to-end.""",

    "cli-and-api": """Document all CLI commands and programmatic APIs. Include:
## CLI Reference
For each CLI command/subcommand found:
### `command-name`
| Option | Type | Default | Description |
|--------|------|---------|-------------|
List all flags and arguments. Show a usage example.
## Programmatic API
For each public class/function intended for external use:
### `ClassName` / `function_name`
- Signature
- Parameters table
- Return value
- Example usage (code block)
## Integration Examples
Show how to use the CLI and API together in a realistic workflow.""",

    "installation-and-setup": """Write a complete installation and setup guide. Include:
## Requirements
System requirements, language versions, dependencies.
## Installation Methods
### From Source
Step-by-step using build_commands found in the analysis.
### Via Package Manager
If pyproject.toml / package.json found, show pip/uv/npm install commands.
### Docker
If Dockerfile found, show docker build and run commands.
## First Run
Walk through running the project for the first time.
## Environment Variables
Any configuration via env vars found in the evidence/config files.
## Troubleshooting
Common setup issues and how to resolve them.""",

    "configuration": """Document all configuration options. Include:
## Configuration Files
List every config file found (YAML, TOML, JSON, .env) with its purpose.
## Configuration Reference
For each config file, a full table:
| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
## Configuration Examples
Show a minimal config and a full-featured config as code blocks.
## Runtime Configuration
Any CLI flags or env vars that override file-based config.
## Validation
Describe how config is validated (Pydantic models, schema, etc.).""",

    "testing": """Document the testing strategy and how to run tests. Include:
## Testing Philosophy
What is tested, what the coverage goals are, and the testing approach.
## Test Structure
Directory layout of tests. Which directories/files contain which kinds of tests.
## Running Tests
Use test_commands from analysis data. Show:
```bash
# unit tests
# integration tests
# with coverage
```
## Test Categories
### Unit Tests
What units are tested, key fixtures/mocks.
### Integration Tests
What integrations are exercised.
## Writing New Tests
Conventions to follow, where to put new tests, how to run a single test.
## CI/CD
If CI config found in evidence, describe the pipeline.""",

    "ecosystem-and-integrations": """Document external integrations, plugins, and the broader ecosystem. Include:
## External Dependencies
Table of all significant third-party libraries: name, version, purpose.
## Integrations
For each external system or service the project integrates with:
### Integration Name
- What it does
- How it's configured
- Code reference (file/class)
## Extension Points
Plugin interfaces, hooks, or extension mechanisms found in the codebase.
## Related Projects
Similar tools or projects in the same space (based on evidence in README/docs if found).
## Roadmap / Known Limitations
Any TODOs, FIXMEs, or risk items found in the analysis.""",
}


class PageBuilder:
    """Generate wiki pages from an AnalysisResult using an LLM.

    If a wiki page already exists on disk with `pin: true` in its YAML
    frontmatter it is left unchanged.  `prompt_overrides` in config.yml
    can customise the per-page user prompt.
    """

    def __init__(
        self,
        llm_config: LLMConfig,
        prompt_overrides: dict[str, str] | None = None,
        exclude_pages: list[str] | None = None,
        wiki_dir: Path | None = None,
    ) -> None:
        self._client = LLMClient(llm_config)
        self._overrides = prompt_overrides or {}
        self._exclude = set(exclude_pages or [])
        self._wiki_dir = wiki_dir
        self._system = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

    def build(self, combined: AnalysisResult) -> dict[str, tuple[str, str]]:
        """Return {slug: (title, markdown_content)} for each page."""
        results: dict[str, tuple[str, str]] = {}
        for slug in CANONICAL_PAGES:
            page = self.build_one(slug, combined)
            if page:
                results[slug] = page
        return results

    def build_one(self, slug: str, combined: AnalysisResult, _payload: dict | None = None) -> tuple[str, str] | None:
        """Build a single wiki page. Returns (title, content) or None if skipped.

        Pass a pre-built *_payload* dict to avoid recomputing it for every page
        when calling build_one in parallel (payload is the same for all pages).
        """
        if slug not in _PAGE_FOCUS and slug not in self._overrides:
            return None
        if slug in self._exclude:
            return None
        if self._wiki_dir and _is_pinned(self._wiki_dir / f"{slug}.md"):
            existing = (self._wiki_dir / f"{slug}.md").read_text()
            title = _extract_title(existing) or slug
            return (title, existing)

        payload = _payload if _payload is not None else _build_payload(combined)
        focus = self._overrides.get(slug) or _PAGE_FOCUS[slug]
        user_prompt = (
            f"Task: {focus}\n\n"
            f"Analysis data (JSON):\n{json.dumps(payload, ensure_ascii=False)}"
        )

        try:
            raw = self._client.call(user_prompt, system=self._system)
            title, content = _parse_llm_response(raw, slug)
        except Exception as exc:  # noqa: BLE001
            title = slug.replace("-", " ").title()
            content = f"# {title}\n\n> *LLM synthesis failed: {exc}*\n"

        content = _ensure_frontmatter(slug, title, content)
        return (title, content)


# ── helpers ──────────────────────────────────────────────────────────

def _build_payload(combined: AnalysisResult) -> dict:
    # Build a compact symbol index: name -> {file, line_start, line_end, kind}
    symbol_index = {
        s.name: {
            "file": s.file,
            "line_start": s.line_start,
            "line_end": s.line_end,
            "kind": s.kind,
        }
        for s in combined.symbols[:600]
    }
    return {
        "files_seen": combined.files_seen[:500],
        "entry_points": combined.entry_points,
        "symbols": [s.model_dump() for s in combined.symbols[:600]],
        "symbol_index": symbol_index,
        "relationships": [r.model_dump(by_alias=True) for r in combined.relationships[:600]],
        "build_commands": combined.build_commands,
        "test_commands": combined.test_commands,
        "risks": combined.risks,
        "evidence": combined.evidence,
    }


def _is_pinned(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return bool(re.search(r"^pin:\s*true", text, re.MULTILINE))


def _extract_title(content: str) -> str | None:
    m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    return m.group(1).strip() if m else None


def _parse_llm_response(raw: str, slug: str) -> tuple[str, str]:
    """LLM now returns plain Markdown. Extract title from first H1."""
    raw = raw.strip()
    # Strip accidental outer fences
    raw = re.sub(r"^```(?:markdown)?\s*\n", "", raw)
    raw = re.sub(r"\n```\s*$", "", raw)
    title = _extract_title(raw) or slug.replace("-", " ").title()
    return title, raw


def _ensure_frontmatter(slug: str, title: str, content: str) -> str:
    if content.startswith("---"):
        return content
    fm = f"---\nslug: {slug}\ntitle: \"{title}\"\npin: false\n---\n\n"
    return fm + content
