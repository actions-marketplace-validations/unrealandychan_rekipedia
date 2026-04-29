"""Build wiki pages from combined AnalysisResult using the LLM."""
from __future__ import annotations

import json
import re
from pathlib import Path

from close_wiki.llm.client import LLMClient
from close_wiki.models.contracts import AnalysisResult, LLMConfig

_SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "digest_system.md"

# The 5 canonical pages every project wiki should have
CANONICAL_PAGES = [
    "index",
    "architecture",
    "core-modules",
    "build-and-deploy",
    "testing-strategy",
]

_PAGE_FOCUS: dict[str, str] = {
    "index": "Give a high-level overview of the whole project: what it does, who it's for, and the main entry points.",
    "architecture": "Describe the overall architecture: major components, how they interact, data flow, and key design decisions.",
    "core-modules": "Focus on the most important modules/packages: what each does, its public API, and key classes/functions.",
    "build-and-deploy": "Explain how to build, run, and deploy the project. Include all commands discovered in config files.",
    "testing-strategy": "Describe how the project is tested: frameworks used, test locations, how to run tests, coverage approach.",
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
        """Return {slug: (title, markdown_content)} for each page.

        Pages that are pinned on disk or excluded in config are skipped.
        """
        payload = _build_payload(combined)
        results: dict[str, tuple[str, str]] = {}

        for slug in CANONICAL_PAGES:
            if slug in self._exclude:
                continue
            if self._wiki_dir and _is_pinned(self._wiki_dir / f"{slug}.md"):
                # Keep existing content
                existing = (self._wiki_dir / f"{slug}.md").read_text()
                title = _extract_title(existing) or slug
                results[slug] = (title, existing)
                continue

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

            # Add YAML frontmatter
            content = _ensure_frontmatter(slug, title, content)
            results[slug] = (title, content)

        return results


# ── helpers ──────────────────────────────────────────────────────────

def _build_payload(combined: AnalysisResult) -> dict:
    return {
        "files_seen": combined.files_seen[:200],
        "entry_points": combined.entry_points,
        "symbols": [s.model_dump() for s in combined.symbols[:300]],
        "relationships": [r.model_dump(by_alias=True) for r in combined.relationships[:300]],
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
    """Try to extract a structured response; fall back to raw markdown."""
    raw = raw.strip()
    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json|markdown)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
        title = data.get("title") or slug.replace("-", " ").title()
        summary = data.get("summary", "")
        key_concepts = data.get("key_concepts", [])
        symbols = data.get("symbols", [])
        risks = data.get("risks", [])
        build_commands = data.get("build_commands", [])
        test_commands = data.get("test_commands", [])
        mermaid = data.get("mermaid_graph", "")

        lines = [f"# {title}\n", summary, ""]
        if key_concepts:
            lines += ["## Key Concepts", ""] + [f"- {c}" for c in key_concepts] + [""]
        if symbols:
            lines += ["## Symbols", ""]
            for s in symbols[:20]:
                lines.append(f"- **`{s.get('name', '')}`** ({s.get('kind', '')}) — {s.get('description', '')}")
            lines.append("")
        if build_commands:
            lines += ["## Build Commands", "```bash"] + build_commands + ["```", ""]
        if test_commands:
            lines += ["## Test Commands", "```bash"] + test_commands + ["```", ""]
        if risks:
            lines += ["## Risks / Notes", ""] + [f"- {r}" for r in risks] + [""]
        if mermaid:
            lines += ["## Diagram", "```mermaid", mermaid, "```", ""]

        return title, "\n".join(lines)
    except (json.JSONDecodeError, KeyError):
        # LLM returned plain markdown — use as-is
        title = _extract_title(raw) or slug.replace("-", " ").title()
        return title, raw


def _ensure_frontmatter(slug: str, title: str, content: str) -> str:
    if content.startswith("---"):
        return content
    fm = f"---\nslug: {slug}\ntitle: \"{title}\"\npin: false\n---\n\n"
    return fm + content
