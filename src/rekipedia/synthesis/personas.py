"""Persona style instructions prepended to the PageBuilder system prompt.

Each persona reshapes how the LLM writes wiki pages:

  junior-dev  Simplified explanations, high verbosity, tutorial-like, focuses on basic patterns
  senior-dev  Comprehensive overview, detailed explanations, focuses on patterns and consequences
  pm          High-level, business-focused, less technical jargon, focuses on domain features and workflows
"""
from __future__ import annotations

__all__ = ["PERSONA_CHOICES", "persona_preamble"]

PERSONA_CHOICES = ["junior-dev", "senior-dev", "pm"]

_PREAMBLES: dict[str, str] = {
    "junior-dev": """\
## Target Audience Persona: Junior Developer
Your target reader is a **Junior Developer** new to this codebase.
- Provide simple, patient, and step-by-step explanations of modules, classes, and algorithms.
- Explain common design patterns used in the code (e.g. Repository pattern, Service pattern) and why they are used.
- Include clear working code snippets and use cases.
- Explain technical jargon clearly when first introduced.
- Do not assume extensive prior knowledge of the project's architecture or libraries.
""",

    "senior-dev": "",  # Default detailed wiki

    "pm": """\
## Target Audience Persona: Project Manager / Tech Lead
Your target reader is a **Product Manager or business stakeholder**.
- Focus on high-level business capabilities, workflows, user-facing features, and domain logic.
- Avoid low-level technical implementation details, syntax-level code snippets, or helper function lists.
- Explain the codebase structure in terms of business modules and domain layers.
- Highlight project risks, dependencies on third-party services, and business requirements.
- Use clear, non-technical or high-level business language suitable for product roadmap planning and alignment.
""",
}

def persona_preamble(persona: str) -> str:
    """Return the system-prompt preamble for the given persona.

    Returns an empty string for 'senior-dev' (no override).
    Raises ValueError for unknown personas.
    """
    if persona not in _PREAMBLES:
        raise ValueError(
            f"Unknown persona {persona!r}. "
            f"Choose from: {', '.join(PERSONA_CHOICES)}"
        )
    return _PREAMBLES[persona]
