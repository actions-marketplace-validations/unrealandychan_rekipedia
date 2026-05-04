"""Java source extractor using tree-sitter."""
# Copyright 2026 Eddie Chan. All rights reserved.
from __future__ import annotations

from pathlib import Path

import tree_sitter_java as tsj
from tree_sitter import Language, Parser

from rekipedia.extractors.base import BaseExtractor
from rekipedia.models.contracts import AnalysisResult, Relationship, Symbol

_JAVA_LANG = Language(tsj.language())
_PARSER = Parser(_JAVA_LANG)


def _node_text(node: object, src: bytes) -> str:
    """Return the decoded text of a tree-sitter node."""
    n = node  # type: ignore[assignment]
    return src[n.start_byte : n.end_byte].decode("utf-8", errors="replace")


def _walk(node: object):  # type: ignore[override]
    """Yield all descendant nodes (depth-first)."""
    stack = list(getattr(node, "named_children", []))
    while stack:
        cur = stack.pop(0)
        yield cur
        stack = list(getattr(cur, "named_children", [])) + stack


class JavaExtractor(BaseExtractor):
    """Extract symbols and relationships from Java source files."""

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".java"

    def extract(self, path: Path, repo_root: Path) -> AnalysisResult:
        rel = str(path.relative_to(repo_root))
        try:
            src_bytes = path.read_bytes()
        except OSError:
            return AnalysisResult(shard_id=rel, files_seen=[rel], entry_points=[])

        tree = _PARSER.parse(src_bytes)
        root = tree.root_node

        symbols: list[Symbol] = []
        relationships: list[Relationship] = []
        entry_points: list[str] = []

        for node in _walk(root):
            ntype = node.type  # type: ignore[attr-defined]

            # ── imports ──────────────────────────────────────────────────
            if ntype == "import_declaration":
                # Flatten the scoped_identifier
                for child in node.named_children:  # type: ignore[attr-defined]
                    if child.type in ("scoped_identifier", "identifier"):
                        import_path = _node_text(child, src_bytes)
                        relationships.append(
                            Relationship.model_validate(
                                {"from": rel, "to": import_path, "kind": "import",
                                 "file": rel, "confidence": 1.0, "evidence_tag": "EXTRACTED"}
                            )
                        )

            # ── classes ──────────────────────────────────────────────────
            elif ntype == "class_declaration":
                name_node = node.child_by_field_name("name")  # type: ignore[attr-defined]
                if name_node is None:
                    for child in node.named_children:  # type: ignore[attr-defined]
                        if child.type == "identifier":
                            name_node = child
                            break
                if name_node is not None:
                    cname = _node_text(name_node, src_bytes)
                    symbols.append(
                        Symbol(
                            name=cname,
                            kind="class",
                            file=rel,
                            line_start=node.start_point[0] + 1,  # type: ignore[attr-defined]
                            line_end=node.end_point[0] + 1,  # type: ignore[attr-defined]
                        )
                    )
                    # Inheritance: extends
                    super_node = node.child_by_field_name("superclass")  # type: ignore[attr-defined]
                    if super_node is not None:
                        for child in super_node.named_children:  # type: ignore[attr-defined]
                            if child.type == "type_identifier":
                                base_name = _node_text(child, src_bytes)
                                relationships.append(
                                    Relationship.model_validate(
                                        {"from": cname, "to": base_name, "kind": "inherits",
                                         "file": rel, "confidence": 1.0, "evidence_tag": "EXTRACTED"}
                                    )
                                )
                    # Interfaces: implements
                    ifaces_node = node.child_by_field_name("interfaces")  # type: ignore[attr-defined]
                    if ifaces_node is not None:
                        for child in _walk(ifaces_node):
                            if child.type == "type_identifier":  # type: ignore[attr-defined]
                                iface_name = _node_text(child, src_bytes)
                                relationships.append(
                                    Relationship.model_validate(
                                        {"from": cname, "to": iface_name, "kind": "uses",
                                         "file": rel, "confidence": 1.0, "evidence_tag": "EXTRACTED"}
                                    )
                                )

            # ── interfaces ───────────────────────────────────────────────
            elif ntype == "interface_declaration":
                name_node = node.child_by_field_name("name")  # type: ignore[attr-defined]
                if name_node is None:
                    for child in node.named_children:  # type: ignore[attr-defined]
                        if child.type == "identifier":
                            name_node = child
                            break
                if name_node is not None:
                    iname = _node_text(name_node, src_bytes)
                    symbols.append(
                        Symbol(
                            name=iname,
                            kind="interface",
                            file=rel,
                            line_start=node.start_point[0] + 1,  # type: ignore[attr-defined]
                            line_end=node.end_point[0] + 1,  # type: ignore[attr-defined]
                        )
                    )

            # ── methods ──────────────────────────────────────────────────
            elif ntype == "method_declaration":
                name_node = node.child_by_field_name("name")  # type: ignore[attr-defined]
                if name_node is None:
                    for child in node.named_children:  # type: ignore[attr-defined]
                        if child.type == "identifier":
                            name_node = child
                            break
                if name_node is not None:
                    mname = _node_text(name_node, src_bytes)
                    symbols.append(
                        Symbol(
                            name=mname,
                            kind="function",
                            file=rel,
                            line_start=node.start_point[0] + 1,  # type: ignore[attr-defined]
                            line_end=node.end_point[0] + 1,  # type: ignore[attr-defined]
                        )
                    )
                    # Detect main entry point
                    if mname == "main":
                        entry_points = [rel]

        return AnalysisResult(
            shard_id=rel,
            files_seen=[rel],
            entry_points=entry_points,
            symbols=symbols,
            relationships=relationships,
        )
