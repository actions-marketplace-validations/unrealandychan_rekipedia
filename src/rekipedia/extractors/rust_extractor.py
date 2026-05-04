"""Rust source extractor using tree-sitter."""
# Copyright 2026 Eddie Chan. All rights reserved.
from __future__ import annotations

from pathlib import Path

import tree_sitter_rust as tsr
from tree_sitter import Language, Parser

from rekipedia.extractors.base import BaseExtractor
from rekipedia.models.contracts import AnalysisResult, Relationship, Symbol

_RUST_LANG = Language(tsr.language())
_PARSER = Parser(_RUST_LANG)


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


def _use_path(node: object, src: bytes) -> str:
    """Flatten a use_declaration's path to a dotted string."""
    ntype = getattr(node, "type", "")
    if ntype in ("identifier", "type_identifier"):
        return _node_text(node, src)
    if ntype == "scoped_identifier":
        parts = []
        for child in getattr(node, "named_children", []):
            parts.append(_use_path(child, src))
        return "::".join(parts)
    if ntype == "scoped_use_list":
        path_node = getattr(node, "named_children", [None])[0]
        return _node_text(path_node, src) if path_node else ""
    return _node_text(node, src)


class RustExtractor(BaseExtractor):
    """Extract symbols and relationships from Rust source files."""

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".rs"

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

            # ── use declarations ─────────────────────────────────────────
            if ntype == "use_declaration":
                # The first named child holds the path
                children = node.named_children  # type: ignore[attr-defined]
                if children:
                    path_str = _use_path(children[0], src_bytes)
                    if path_str:
                        relationships.append(
                            Relationship.model_validate(
                                {"from": rel, "to": path_str, "kind": "import",
                                 "file": rel, "confidence": 1.0, "evidence_tag": "EXTRACTED"}
                            )
                        )

            # ── functions ────────────────────────────────────────────────
            elif ntype == "function_item":
                name_node = node.child_by_field_name("name")  # type: ignore[attr-defined]
                if name_node is None:
                    for child in node.named_children:  # type: ignore[attr-defined]
                        if child.type == "identifier":
                            name_node = child
                            break
                if name_node is not None:
                    fname = _node_text(name_node, src_bytes)
                    start_line = node.start_point[0] + 1  # type: ignore[attr-defined]
                    end_line = node.end_point[0] + 1  # type: ignore[attr-defined]
                    symbols.append(
                        Symbol(
                            name=fname,
                            kind="function",
                            file=rel,
                            line_start=start_line,
                            line_end=end_line,
                        )
                    )
                    if fname == "main":
                        entry_points = [rel]

            # ── structs ──────────────────────────────────────────────────
            elif ntype == "struct_item":
                name_node = node.child_by_field_name("name")  # type: ignore[attr-defined]
                if name_node is None:
                    for child in node.named_children:  # type: ignore[attr-defined]
                        if child.type == "type_identifier":
                            name_node = child
                            break
                if name_node is not None:
                    sname = _node_text(name_node, src_bytes)
                    symbols.append(
                        Symbol(
                            name=sname,
                            kind="type",
                            file=rel,
                            line_start=node.start_point[0] + 1,  # type: ignore[attr-defined]
                            line_end=node.end_point[0] + 1,  # type: ignore[attr-defined]
                            signature=f"struct {sname}",
                        )
                    )

            # ── traits ───────────────────────────────────────────────────
            elif ntype == "trait_item":
                name_node = node.child_by_field_name("name")  # type: ignore[attr-defined]
                if name_node is None:
                    for child in node.named_children:  # type: ignore[attr-defined]
                        if child.type == "type_identifier":
                            name_node = child
                            break
                if name_node is not None:
                    tname = _node_text(name_node, src_bytes)
                    symbols.append(
                        Symbol(
                            name=tname,
                            kind="interface",
                            file=rel,
                            line_start=node.start_point[0] + 1,  # type: ignore[attr-defined]
                            line_end=node.end_point[0] + 1,  # type: ignore[attr-defined]
                            signature=f"trait {tname}",
                        )
                    )

            # ── impl blocks — record uses relationship ───────────────────
            elif ntype == "impl_item":
                # impl Foo for Bar -> uses relationship
                type_node = node.child_by_field_name("type")  # type: ignore[attr-defined]
                trait_node = node.child_by_field_name("trait")  # type: ignore[attr-defined]
                if type_node is not None and trait_node is not None:
                    type_name = _node_text(type_node, src_bytes)
                    trait_name = _node_text(trait_node, src_bytes)
                    relationships.append(
                        Relationship.model_validate(
                            {"from": type_name, "to": trait_name, "kind": "uses",
                             "file": rel, "confidence": 1.0, "evidence_tag": "EXTRACTED"}
                        )
                    )

        return AnalysisResult(
            shard_id=rel,
            files_seen=[rel],
            entry_points=entry_points,
            symbols=symbols,
            relationships=relationships,
        )
