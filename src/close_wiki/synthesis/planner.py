"""PlannerAgent — decides wiki structure dynamically from analysis data."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from close_wiki.llm.client import LLMClient
from close_wiki.models.contracts import AnalysisResult, LLMConfig

logger = logging.getLogger("close_wiki.planner")

_SYSTEM_PROMPT = """\
You are a technical documentation architect. Your job is to analyse a software repository's
static-analysis data and design the OPTIMAL wiki structure for it.

You will receive a JSON summary of the codebase. Based on what is actually present, decide:
- How many wiki pages to generate (could be 3 for a tiny CLI tool, or 15 for a large framework)
- What each page should cover (title, slug, focus)
- What analysis data each page actually needs (don't send everything to everyone)
- The best navigation order for a developer reading the docs for the first time
- Tags/categories for searchability

Output a single JSON object — no markdown fences, no explanation:

{
  "pages": [
    {
      "slug": "lowercase-hyphenated",
      "title": "Human Readable Title",
      "priority": 1,
      "focus": "Detailed multi-sentence instruction for what this page should contain and how to structure it. Include required section headings.",
      "required_data": ["files_seen", "entry_points", "symbols", "relationships", "build_commands", "test_commands", "risks", "evidence", "symbol_index", "pre_built_module_graph", "pre_built_dependency_graph"],
      "tags": ["overview", "getting-started"]
    }
  ],
  "nav_order": ["slug1", "slug2"],
  "index_slug": "index"
}

## Page design rules

### Always include (if data supports it):
- An `index` / overview page (entry point for all readers)
- An `architecture` page if there are ≥3 modules with relationships
- An installation/setup page if build_commands or a package manifest is found

### Only include if data justifies it:
- `testing` only if test files or test_commands exist
- `cli-and-api` only if CLI symbols or HTTP handlers are found
- `configuration` only if config files or env-var evidence exists
- `algorithms` only if there are non-trivial processing pipelines
- `ecosystem-and-integrations` only if ≥3 external dependencies are found

### Split pages when a topic is large:
- If a repo has >5 major modules, split into multiple module pages (e.g. `core-engine`, `cli-layer`, `storage-layer`)
- If architecture is complex, split into `architecture-overview` and `architecture-data-flow`

### required_data minimisation (critical for performance):
- `index` needs: files_seen, entry_points, build_commands, symbol_index, pre_built_module_graph
- `architecture` needs: relationships, entry_points, symbols, pre_built_module_graph, pre_built_dependency_graph, symbol_index
- `testing` needs: test_commands, symbols (filtered to test files), risks
- `installation-and-setup` needs: build_commands, evidence, files_seen
- `configuration` needs: evidence, risks, files_seen
Only request `symbols` and `relationships` for pages that genuinely need deep code analysis.

### Navigation order (nav_order):
Order pages so a new developer can read them top-to-bottom and build understanding progressively:
index → architecture → core concepts → how-to pages → reference → advanced

### Tags (for search):
Assign 2–4 tags per page from: overview, architecture, getting-started, reference, api, cli, testing, configuration, algorithms, deployment, modules, internals, ecosystem
"""


class WikiPlan:
    """The output of PlannerAgent — a structured plan for wiki generation."""

    def __init__(self, data: dict) -> None:
        self.pages: list[dict] = data.get("pages", [])
        self.nav_order: list[str] = data.get("nav_order", [s["slug"] for s in self.pages])
        self.index_slug: str = data.get("index_slug", "index")

    def get_page(self, slug: str) -> dict | None:
        return next((p for p in self.pages if p["slug"] == slug), None)

    def __repr__(self) -> str:
        slugs = [p["slug"] for p in self.pages]
        return f"WikiPlan({len(self.pages)} pages: {slugs})"


class PlannerAgent:
    """One LLM call that designs the entire wiki structure."""

    def __init__(self, llm_config: LLMConfig) -> None:
        self._client = LLMClient(llm_config)

    def plan(self, combined: AnalysisResult, diagrams: dict | None = None) -> WikiPlan:
        """Analyse *combined* and return a WikiPlan.

        Falls back to a sensible default plan if the LLM call fails.
        """
        summary = _build_planning_summary(combined, diagrams)
        prompt = f"Repository analysis data:\n{json.dumps(summary, ensure_ascii=False)}"

        try:
            raw = self._client.call(prompt, system=_SYSTEM_PROMPT)
            raw = raw.strip()
            raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
            raw = re.sub(r"\n?```\s*$", "", raw)
            data = json.loads(raw)
            plan = WikiPlan(data)
            logger.debug("PlannerAgent designed %d pages: %s", len(plan.pages), [p["slug"] for p in plan.pages])
            return plan
        except Exception as exc:
            logger.warning("PlannerAgent failed (%s) — using default plan", exc)
            return _default_plan(combined)


def _build_planning_summary(combined: AnalysisResult, diagrams: dict | None) -> dict:
    """Compact summary for the planner — enough to make structural decisions."""
    # Count files by extension
    ext_counts: dict[str, int] = {}
    for f in combined.files_seen:
        ext = Path(f).suffix.lower() or "(no ext)"
        ext_counts[ext] = ext_counts.get(ext, 0) + 1

    # Count symbols by kind
    kind_counts: dict[str, int] = {}
    for s in combined.symbols:
        kind_counts[s.kind] = kind_counts.get(s.kind, 0) + 1

    # Detect what's present
    has_tests = any(
        "test" in f.lower() or "spec" in f.lower()
        for f in combined.files_seen
    ) or bool(combined.test_commands)

    has_cli = any(
        any(kw in (s.name or "").lower() for kw in ("cli", "command", "cmd", "click", "argparse", "argv"))
        for s in combined.symbols
    ) or any(kw in str(combined.evidence).lower() for kw in ("click", "argparse"))

    has_config = any(
        Path(f).suffix.lower() in (".yaml", ".yml", ".toml", ".json", ".env", ".cfg", ".ini")
        for f in combined.files_seen
    ) or bool(combined.evidence)

    # Top-level modules/directories
    top_dirs = sorted({
        Path(f).parts[0] for f in combined.files_seen if "/" in f
    })

    # Sample of symbols for planner context (just names + kinds, not full dump)
    symbol_sample = [
        {"name": s.name, "kind": s.kind, "file": s.file}
        for s in combined.symbols[:80]
    ]

    return {
        "file_count": len(combined.files_seen),
        "file_extensions": ext_counts,
        "top_level_dirs": top_dirs[:20],
        "entry_points": combined.entry_points[:10],
        "symbol_count": len(combined.symbols),
        "symbol_kinds": kind_counts,
        "symbol_sample": symbol_sample,
        "relationship_count": len(combined.relationships),
        "build_commands": combined.build_commands[:10],
        "test_commands": combined.test_commands[:10],
        "has_tests": has_tests,
        "has_cli": has_cli,
        "has_config": has_config,
        "risks_count": len(combined.risks),
        "evidence_keys": list(combined.evidence.keys())[:20],
        "diagram_names": list((diagrams or {}).keys()),
    }


def _default_plan(combined: AnalysisResult) -> WikiPlan:
    """Fallback plan when LLM planning fails — uses heuristics."""
    has_tests = any("test" in f.lower() for f in combined.files_seen) or bool(combined.test_commands)
    has_cli = any("cli" in f.lower() or "cmd" in f.lower() for f in combined.files_seen)
    has_config = bool(combined.evidence) or bool(combined.build_commands)

    pages = [
        {
            "slug": "index",
            "title": "Project Overview",
            "priority": 1,
            "focus": "Write a comprehensive project overview: what it does, key features, quick start, and project structure with a Mermaid diagram.",
            "required_data": ["files_seen", "entry_points", "build_commands", "symbol_index", "pre_built_module_graph"],
            "tags": ["overview", "getting-started"],
        },
        {
            "slug": "architecture",
            "title": "Architecture",
            "priority": 2,
            "focus": "System architecture: major components, data flow, design decisions. Embed pre_built_module_graph if available.",
            "required_data": ["relationships", "entry_points", "symbols", "pre_built_module_graph", "pre_built_dependency_graph", "symbol_index"],
            "tags": ["architecture", "internals"],
        },
        {
            "slug": "core-modules",
            "title": "Core Modules",
            "priority": 3,
            "focus": "Document every significant module: purpose, public API, key classes/functions with source citations.",
            "required_data": ["symbols", "relationships", "files_seen", "symbol_index"],
            "tags": ["modules", "reference", "api"],
        },
    ]

    if has_cli:
        pages.append({
            "slug": "cli-and-api",
            "title": "CLI & API Reference",
            "priority": 4,
            "focus": "Document all CLI commands with options tables and usage examples. Document programmatic API.",
            "required_data": ["symbols", "entry_points", "files_seen", "symbol_index"],
            "tags": ["cli", "api", "reference"],
        })

    if has_config:
        pages.append({
            "slug": "installation-and-setup",
            "title": "Installation & Setup",
            "priority": 5,
            "focus": "Complete installation guide: requirements, installation methods, first run, env vars, troubleshooting.",
            "required_data": ["build_commands", "evidence", "files_seen"],
            "tags": ["getting-started", "deployment"],
        })

    if has_tests:
        pages.append({
            "slug": "testing",
            "title": "Testing",
            "priority": 6,
            "focus": "Testing strategy, test structure, how to run tests, how to write new tests.",
            "required_data": ["test_commands", "symbols", "files_seen"],
            "tags": ["testing"],
        })

    nav_order = [p["slug"] for p in sorted(pages, key=lambda x: x["priority"])]
    return WikiPlan({"pages": pages, "nav_order": nav_order, "index_slug": "index"})
