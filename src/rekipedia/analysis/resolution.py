"""Symbol resolution pass — links call/import edges to actual definitions."""
from __future__ import annotations

from collections import defaultdict

from rekipedia.models.contracts import AnalysisResult, Relationship


def resolve_relationships(combined: AnalysisResult) -> AnalysisResult:
    """Post-process an AnalysisResult to resolve 'to' names to actual symbol definitions.

    Resolution priority:
    1. Same-file definition (highest confidence)
    2. Unique name across all files
    3. Multiple definitions — leave unresolved (resolved_to_file stays None)

    Returns a new AnalysisResult with resolved_to_file/resolved_to_line set where possible.
    """
    # Build index: name -> list of (file, line_start)
    name_index: dict[str, list[tuple[str, int | None]]] = defaultdict(list)
    for sym in combined.symbols:
        name_index[sym.name].append((sym.file, sym.line_start))

    resolved_rels: list[Relationship] = []
    for rel in combined.relationships:
        candidates = name_index.get(rel.to, [])
        resolved_file: str | None = None
        resolved_line: int | None = None

        if candidates:
            if len(candidates) == 1:
                # Unique — resolve directly
                resolved_file, resolved_line = candidates[0]
            else:
                # Multiple — prefer same-file as relationship source
                same_file = [(f, ln) for f, ln in candidates if f == rel.file]
                if same_file:
                    resolved_file, resolved_line = same_file[0]
                # else: ambiguous, leave unresolved

        # Build new relationship with resolved fields
        rel_data = rel.model_dump(by_alias=True)
        rel_data["resolved_to_file"] = resolved_file
        rel_data["resolved_to_line"] = resolved_line
        resolved_rels.append(Relationship.model_validate(rel_data))

    return combined.model_copy(update={"relationships": resolved_rels})
