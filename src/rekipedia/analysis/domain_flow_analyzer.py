"""LLM-driven Business Domain Analyzer — extracts Domain → Flow → Step hierarchy."""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

if TYPE_CHECKING:
    from rekipedia.models.contracts import AnalysisResult

logger = logging.getLogger("rekipedia.analysis.domain_flow_analyzer")

# ── Pydantic models ───────────────────────────────────────────────────────────


class StepNode(BaseModel):
    id: str  # "step:<flow>:<name>" kebab-case
    name: str
    summary: str
    tags: list[str]
    complexity: Literal["simple", "moderate", "complex"]
    file_path: str = ""
    line_range: tuple[int, int] = (0, 0)


class FlowNode(BaseModel):
    id: str  # "flow:<name>"
    name: str
    summary: str
    tags: list[str]
    complexity: Literal["simple", "moderate", "complex"]
    entry_point: str = ""
    entry_type: Literal["http", "cli", "event", "cron", "manual"] = "manual"
    steps: list[StepNode] = []


class DomainNode(BaseModel):
    id: str  # "domain:<name>"
    name: str
    summary: str
    tags: list[str]
    complexity: Literal["simple", "moderate", "complex"]
    entities: list[str] = []
    business_rules: list[str] = []
    cross_domain_interactions: list[str] = []
    flows: list[FlowNode] = []


class BizDomainGraph(BaseModel):
    version: str = "1.0.0"
    project_name: str = ""
    analyzed_at: str = ""
    domains: list[DomainNode] = []


# ── Prompt construction ───────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are an expert software architect who extracts business domain knowledge from codebases.
Given a list of symbols, relationships, and entry points, identify the business domains,
their workflows (flows), and the concrete implementation steps within each flow.

Rules:
- Use ACTUAL business terminology found in the code — no invented flows.
- Return ONLY valid JSON matching the schema. No markdown, no prose.
- Identify 2-6 top-level domains.
- Each domain must have 2-5 flows.
- Each flow must have 3-8 steps.
- IDs must follow kebab-case patterns: domain:<name>, flow:<name>, step:<flow>:<name>.
"""

_USER_PROMPT_TEMPLATE = """\
Analyse the following codebase and produce a BizDomainGraph JSON document.

## Project: {project_name}

## Entry Points
{entry_points}

## Key Symbols (top {sym_count})
{symbols_block}

## Relationships (sample)
{relationships_block}

## Schema
```json
{schema}
```

Return ONLY the JSON object matching BizDomainGraph. No markdown fences.
"""


def _build_prompt(analysis_result: AnalysisResult, project_name: str) -> str:
    # Top 200 symbols — prefer functions/classes over variables
    kind_priority = {"function": 0, "class": 1, "route": 2, "interface": 3, "module": 4}
    symbols = sorted(
        analysis_result.symbols,
        key=lambda s: (kind_priority.get(s.kind, 9), s.name),
    )[:200]

    sym_lines = []
    for s in symbols:
        doc = f" — {s.docstring[:80]}" if s.docstring else ""
        loc = f"{s.file}:{s.line_start}" if s.line_start else s.file
        sym_lines.append(f"  [{s.kind}] {s.name} @ {loc}{doc}")

    # Up to 100 relationships
    rel_lines = []
    for r in analysis_result.relationships[:100]:
        rel_lines.append(f"  {r.from_} --[{r.kind}]--> {r.to}")

    entry_lines = "\n".join(f"  - {ep}" for ep in (analysis_result.entry_points or []))
    if not entry_lines:
        entry_lines = "  (none detected)"

    schema = BizDomainGraph.model_json_schema()

    return _USER_PROMPT_TEMPLATE.format(
        project_name=project_name or "unknown",
        entry_points=entry_lines,
        sym_count=len(symbols),
        symbols_block="\n".join(sym_lines) or "  (none)",
        relationships_block="\n".join(rel_lines) or "  (none)",
        schema=json.dumps(schema, indent=2),
    )


def _parse_response(raw: str, project_name: str) -> BizDomainGraph:
    """Extract and parse the JSON object from the LLM response."""
    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()

    # Find the outermost JSON object
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        logger.warning("LLM returned no JSON object; returning empty graph")
        return BizDomainGraph(project_name=project_name, analyzed_at=_now())

    obj = json.loads(cleaned[start:end])
    # Ensure top-level fields
    obj.setdefault("project_name", project_name)
    obj.setdefault("analyzed_at", _now())
    return BizDomainGraph.model_validate(obj)


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ── Analyzer class ────────────────────────────────────────────────────────────


class BizDomainAnalyzer:
    """LLM-driven business domain extraction from an AnalysisResult."""

    def __init__(self, llm_client: object = None) -> None:
        # llm_client must have a .call(prompt, *, system) -> str interface (LLMClient).
        # If None, we lazily create one from env/config.
        self._llm_client = llm_client

    def _get_client(self) -> object:
        if self._llm_client is not None:
            return self._llm_client
        # Lazy import to avoid circular deps at module load
        import os

        from rekipedia.llm.client import LLMClient
        from rekipedia.models.contracts import LLMConfig

        config = LLMConfig(
            model=os.environ.get("REKIPEDIA_MODEL", "ollama/llama4"),
            api_key=os.environ.get("REKIPEDIA_API_KEY", ""),
            base_url=os.environ.get("REKIPEDIA_BASE_URL", ""),
        )
        return LLMClient(config)

    def analyze(self, analysis_result: AnalysisResult, project_name: str = "") -> BizDomainGraph:
        """Extract business domain graph from an AnalysisResult."""
        prompt = _build_prompt(analysis_result, project_name)
        client = self._get_client()
        raw = client.call(prompt, system=_SYSTEM_PROMPT)
        return _parse_response(raw, project_name)

    def save(self, graph: BizDomainGraph, output_dir: Path) -> Path:
        """Persist the domain graph to output_dir/.rekipedia/domain-graph.json."""
        dest_dir = Path(output_dir) / ".rekipedia"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "domain-graph.json"
        dest.write_text(graph.model_dump_json(indent=2), encoding="utf-8")
        return dest
