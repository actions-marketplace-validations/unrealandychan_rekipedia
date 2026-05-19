"""Doc-type style instructions prepended to the PageBuilder system prompt.

Each doc-type reshapes how the LLM writes wiki pages:

  default    Standard balanced wiki (architecture overview, module summaries, etc.)
  api-ref    API reference style — function signatures, params, return values, examples
  tutorial   Step-by-step tutorial style — "you will learn", numbered steps, code snippets
  runbook    Ops runbook style — prerequisites, numbered steps, troubleshooting sections
  adr        Architecture Decision Record style — Context / Decision / Consequences
  changelog  Changelog style — What Changed / Why / Migration Notes
"""
from __future__ import annotations

__all__ = ["DOC_TYPE_CHOICES", "doc_type_preamble"]

DOC_TYPE_CHOICES = ["default", "api-ref", "tutorial", "runbook", "adr", "changelog"]

_PREAMBLES: dict[str, str] = {
    "default": "",  # No preamble — use the standard system prompt as-is

    "api-ref": """\
## Doc-Type Override: API Reference
You are writing an **API Reference** wiki.  For every page:
- Lead with a one-sentence summary of the module/component.
- Document each public symbol (function, class, method) with:
  - Signature (exact, copied from source)
  - Parameters table: name | type | default | description
  - Returns: type and meaning
  - Raises: exceptions that can be thrown
  - A short usage example in a fenced code block
- Group symbols by category (Constructors, Methods, Exceptions, Types).
- Do NOT include narrative prose or tutorials.
- Use Markdown headings: `##` for modules, `###` for classes, `####` for methods.
""",

    "tutorial": """\
## Doc-Type Override: Tutorial
You are writing a **Tutorial** wiki aimed at developers new to this codebase.
For every page:
- Open with "In this guide, you will learn how to …"
- Use numbered steps for any procedure.
- Include working code examples (fenced blocks with language tags) for every concept.
- Explain *why*, not just *what*.
- Add a "Prerequisites" section at the top and a "Next Steps" section at the bottom.
- Keep sentences short; avoid jargon without explanation.
- Use callout blockquotes (`> **Note:**`, `> **Warning:**`) for important caveats.
""",

    "runbook": """\
## Doc-Type Override: Ops Runbook
You are writing an **Operations Runbook** for SREs and on-call engineers.
For every page:
- Start with: **Purpose**, **Scope**, **Owner**, **Last Reviewed**.
- List all **Prerequisites** (tools, access, env vars required).
- Write procedures as numbered steps with exact shell commands in fenced blocks.
- Add an **Expected Output** note after each command.
- Include a **Troubleshooting** section with symptom → cause → fix format.
- End with an **Escalation Path** section.
- Be terse; omit background theory unless essential for safety.
""",

    "adr": """\
## Doc-Type Override: Architecture Decision Records (ADR)
You are writing **Architecture Decision Records**.  For every page:
- Use the MADR format with these sections:
  1. **Status**: Proposed | Accepted | Deprecated | Superseded by [ADR-xxx]
  2. **Context**: What situation or problem motivated this decision?
  3. **Decision**: What was decided and why?  Reference specific code/modules.
  4. **Consequences**: What are the positive / negative / neutral outcomes?
  5. **Alternatives Considered**: What other options were evaluated and rejected?
- Number each ADR in the page title (ADR-001, ADR-002, …).
- Keep each ADR focused on ONE architectural decision.
- Use past tense for Context/Decision; present tense for Consequences.
""",

    "changelog": """\
## Doc-Type Override: Changelog
You are writing a **Changelog** wiki for developers and users upgrading the software.
For every page:
- Group changes under: **What Changed**, **Why It Changed**, **Migration Notes**.
- Use Keep a Changelog categories: Added | Changed | Deprecated | Removed | Fixed | Security.
- Each entry must reference the file/module/symbol that changed (e.g. `src/api.py:42`).
- Write migration notes as numbered steps with before/after code examples.
- Be specific — say "renamed `run_digest(no_llm=)` to `run_digest(skip_llm=)`" not "API changes".
- Do NOT include implementation details unrelated to user-facing changes.
""",
}


def doc_type_preamble(doc_type: str) -> str:
    """Return the system-prompt preamble for the given doc-type.

    Returns an empty string for 'default' (no override).
    Raises ValueError for unknown doc-types.
    """
    if doc_type not in _PREAMBLES:
        raise ValueError(
            f"Unknown doc-type {doc_type!r}. "
            f"Choose from: {', '.join(DOC_TYPE_CHOICES)}"
        )
    return _PREAMBLES[doc_type]
