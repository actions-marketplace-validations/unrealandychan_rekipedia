"""Agentic tool-calling planner for wiki structure generation.

Instead of generating a single-shot JSON blob, the LLM incrementally builds
the plan by calling add_section, add_page, and finalize tools.

Environment:
    REKIPEDIA_AGENT_PLANNER=1   — enable agentic planner (default: 0 / off)
"""
from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable

import litellm

from rekipedia.llm.client import LLMCaller
from rekipedia.models.contracts import AnalysisResult, LLMConfig
from rekipedia.synthesis.planner import (
    WikiPlan,
    _build_planning_summary,
    _default_plan,
    _sanitize_slug,
)

logger = logging.getLogger("rekipedia.agent_planner")

_MAX_ITER = 20

_AGENT_SYSTEM_PROMPT = """\
You are a technical documentation architect for software repositories. Use the provided tools to design the OPTIMAL wiki structure — like DeepWiki does for open-source projects.

Call `add_section` first to define sections, then `add_page` for each page (minimum 5 pages, maximum 15).
Finally call `finalize` to set the navigation order and complete the plan.

## importance field (0–100):
Assign an importance score to each page:
- 95–100: index, architecture-overview (always-read pages)
- 80–94: core-module pages, data-flow, repository-structure
- 60–79: api-reference, configuration, testing
- 40–59: internals, algorithms, contributing
- 20–39: ecosystem, deployment, third-party integrations

## keywords field:
List 5–10 exact symbol names, function names, or domain terms that this page covers.
Used for fast retrieval when answering questions about the codebase.

## Section design:
Group pages into logical sections. Only create sections that have ≥2 pages.
Common sections: getting-started, architecture, core-components, api-reference, internals, development, ecosystem.

## Always include these pages (if data supports):
- `index`: Project overview, key features, quick-start snippet, repo structure tree
- `repository-structure`: Full repo layout with annotations (REQUIRED if file_count ≥ 10)
- `architecture-overview`: System diagram, component responsibilities, design decisions
- `technical-debt`: ALWAYS include this page. Importance: 70. Section: development.

## Navigation order:
Order: index → repo-structure → architecture → core-modules → api-reference → internals → development → ecosystem

## Tags (2–4 per page from):
overview, architecture, getting-started, reference, api, cli, testing, configuration, algorithms, deployment, modules, internals, ecosystem, data-flow, repository-structure, contributing
"""

PLANNER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_section",
            "description": "Add a navigation section that groups related pages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Lowercase hyphenated section ID"},
                    "title": {"type": "string", "description": "Human-readable section title"},
                    "pages": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of page slugs in this section",
                    },
                },
                "required": ["id", "title", "pages"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_page",
            "description": "Add a wiki page to the plan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "Lowercase hyphenated page slug"},
                    "title": {"type": "string", "description": "Human-readable page title"},
                    "section": {"type": "string", "description": "Section ID this page belongs to"},
                    "priority": {"type": "integer", "description": "Generation priority (lower = first)"},
                    "importance": {"type": "integer", "description": "Importance score 0-100"},
                    "focus": {"type": "string", "description": "Detailed instructions for the page writer"},
                    "required_data": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Data fields required to generate this page",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "2-4 category tags",
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "5-10 symbol names or domain terms this page covers",
                    },
                },
                "required": ["slug", "title", "section", "priority", "importance", "focus", "required_data"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finalize",
            "description": "Complete the plan by providing final navigation order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nav_order": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Ordered list of page slugs for navigation",
                    },
                    "index_slug": {"type": "string", "description": "Slug of the index/home page"},
                },
                "required": ["nav_order", "index_slug"],
            },
        },
    },
]


class AgentPlanner:
    """Tool-calling agentic planner for wiki structure design.

    Same interface as PlannerAgent: constructor takes llm_config + caller=,
    and .plan() returns WikiPlan.
    """

    def __init__(self, llm_config: LLMConfig | None = None, *, caller: LLMCaller | None = None) -> None:
        self._llm_config = llm_config or LLMConfig()
        self._caller = caller  # may be None; used for model/key resolution only

    def plan(
        self,
        combined: AnalysisResult,
        diagrams: dict | None = None,
        progress_cb: Callable[[str], None] | None = None,
    ) -> WikiPlan:
        """Run agentic planning loop. Returns WikiPlan."""
        summary = _build_planning_summary(combined, diagrams)
        n_files = summary["file_count"]
        n_symbols = summary["symbol_count"]
        prompt = f"Repository analysis data:\n{json.dumps(summary, ensure_ascii=False)}"

        if progress_cb:
            progress_cb(f"🧠 AgentPlanner analysing {n_files} files, {n_symbols} symbols…")

        llm_config = self._llm_config
        model = os.environ.get("REKIPEDIA_MODEL") or llm_config.model
        api_key = os.environ.get("REKIPEDIA_API_KEY") or llm_config.api_key or None
        base_url = os.environ.get("REKIPEDIA_BASE_URL") or llm_config.base_url or None

        kwargs: dict = {
            "model": model,
            "temperature": llm_config.temperature,
            "timeout": 600,
            "tools": PLANNER_TOOLS,
            "tool_choice": "auto",
            "messages": [
                {"role": "system", "content": _AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url

        pages: list[dict] = []
        sections: list[dict] = []
        nav_order: list[str] = []
        index_slug = "index"

        try:
            for _iteration in range(_MAX_ITER):
                response = litellm.completion(**kwargs)
                msg = response.choices[0].message
                tool_calls = getattr(msg, "tool_calls", None) or []

                if not tool_calls:
                    # No more tool calls — done
                    break

                # Append assistant message
                if hasattr(msg, "model_dump"):
                    kwargs["messages"].append(msg.model_dump(exclude_none=True))
                else:
                    kwargs["messages"].append({
                        "role": "assistant",
                        "content": msg.content,
                        "tool_calls": [tc.model_dump() for tc in tool_calls],
                    })

                finalized = False
                for tc in tool_calls:
                    fn_name = tc.function.name
                    try:
                        fn_args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        fn_args = {}

                    result_msg = "ok"

                    if fn_name == "add_section":
                        section = {
                            "id": fn_args.get("id", ""),
                            "title": fn_args.get("title", ""),
                            "pages": fn_args.get("pages", []),
                        }
                        sections.append(section)
                        logger.debug("AgentPlanner: add_section %s", section["id"])
                        result_msg = f"Section '{section['id']}' added."

                    elif fn_name == "add_page":
                        slug = _sanitize_slug(fn_args.get("slug", ""))
                        page = {
                            "slug": slug,
                            "title": fn_args.get("title", ""),
                            "section": fn_args.get("section", ""),
                            "priority": fn_args.get("priority", 50),
                            "importance": fn_args.get("importance", 50),
                            "focus": fn_args.get("focus", ""),
                            "required_data": fn_args.get("required_data", []),
                            "tags": fn_args.get("tags", []),
                            "keywords": fn_args.get("keywords", []),
                        }
                        pages.append(page)
                        logger.debug("AgentPlanner: add_page %s", slug)
                        result_msg = f"Page '{slug}' added."

                    elif fn_name == "finalize":
                        nav_order = [_sanitize_slug(s) for s in fn_args.get("nav_order", [])]
                        index_slug = _sanitize_slug(fn_args.get("index_slug", "index"))
                        finalized = True
                        result_msg = "Plan finalized."

                    kwargs["messages"].append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_msg,
                    })

                if finalized:
                    break

        except Exception as exc:
            logger.warning("AgentPlanner failed (%s) — using default plan", exc)
            if progress_cb:
                progress_cb(f"⚠️  AgentPlanner failed ({type(exc).__name__}), using default plan")
            return _default_plan(combined)

        if not pages:
            logger.warning("AgentPlanner produced no pages — using default plan")
            if progress_cb:
                progress_cb("⚠️  AgentPlanner produced no pages, using default plan")
            return _default_plan(combined)

        data = {
            "pages": pages,
            "sections": sections,
            "nav_order": nav_order,
            "index_slug": index_slug,
        }
        plan = WikiPlan(data)

        if progress_cb:
            section_names = ", ".join(s["title"] for s in sections) or "—"
            progress_cb(
                f"✅ AgentPlan ready: {len(pages)} pages in {len(sections)} sections ({section_names})"
            )

        logger.debug("AgentPlanner designed %d pages: %s", len(pages), [p["slug"] for p in pages])
        return plan
