"""Rust source extractor using tree-sitter — full symbol coverage.

Extracted symbol kinds
----------------------
function    fn items (free functions + associated fn inside impl)
type        struct, enum, type alias
interface   trait definitions
constant    const / static items
macro       macro_rules! definitions
module      mod declarations

Extracted relationship kinds
----------------------------
import      use declarations (flattened path)
uses        impl Trait for Type  →  Type -uses-> Trait
calls       function_item body contains call_expression to a known identifier
"""
from __future__ import annotations

from pathlib import Path

import tree_sitter_rust as tsr
from tree_sitter import Language, Parser

from rekipedia.extractors.base import BaseExtractor
from rekipedia.models.contracts import AnalysisResult, Relationship, Symbol

_RUST_LANG = Language(tsr.language())
_PARSER = Parser(_RUST_LANG)


# ── low-level helpers ────────────────────────────────────────────────────────

def _node_text(node: object, src: bytes) -> str:
    n = node  # type: ignore[assignment]
    return src[n.start_byte : n.end_byte].decode("utf-8", errors="replace")


def _walk(node: object):
    """Yield all descendant nodes (depth-first, pre-order)."""
    stack = list(getattr(node, "named_children", []))
    while stack:
        cur = stack.pop(0)
        yield cur
        stack = list(getattr(cur, "named_children", [])) + stack


def _first_child_of_type(node: object, *types: str) -> object | None:
    for child in getattr(node, "named_children", []):
        if getattr(child, "type", "") in types:
            return child
    return None


def _use_path(node: object, src: bytes) -> str:
    """Flatten a use_declaration path to a '::'-joined string."""
    ntype = getattr(node, "type", "")
    if ntype in ("identifier", "type_identifier"):
        return _node_text(node, src)
    if ntype == "scoped_identifier":
        return "::".join(
            _use_path(c, src) for c in getattr(node, "named_children", [])
        )
    if ntype == "scoped_use_list":
        path_node = getattr(node, "named_children", [None])[0]
        return _node_text(path_node, src) if path_node else ""
    return _node_text(node, src)


def _name_from_field_or_child(node: object, src: bytes, *child_types: str) -> str | None:
    """Return text of field 'name', or first child whose type is in child_types."""
    name_node = getattr(node, "child_by_field_name", lambda _: None)("name")
    if name_node is None:
        name_node = _first_child_of_type(node, *child_types)
    return _node_text(name_node, src) if name_node is not None else None


# ── extractor ────────────────────────────────────────────────────────────────

class RustExtractor(BaseExtractor):
    """Extract symbols and relationships from Rust source files using tree-sitter."""

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".rs"

    def extract(self, path: Path, repo_root: Path) -> AnalysisResult:  # noqa: C901
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

        # Collect names of all top-level functions for call-graph edges
        defined_fns: set[str] = set()

        for node in _walk(root):
            ntype = node.type  # type: ignore[attr-defined]

            # ── use declarations ─────────────────────────────────────────
            if ntype == "use_declaration":
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

            # ── free functions + associated fns ──────────────────────────
            elif ntype == "function_item":
                fname = _name_from_field_or_child(node, src_bytes, "identifier")
                if fname:
                    defined_fns.add(fname)
                    symbols.append(
                        Symbol(
                            name=fname,
                            kind="function",
                            file=rel,
                            line_start=node.start_point[0] + 1,  # type: ignore[attr-defined]
                            line_end=node.end_point[0] + 1,  # type: ignore[attr-defined]
                        )
                    )
                    if fname == "main":
                        entry_points = [rel]

            # ── structs ──────────────────────────────────────────────────
            elif ntype == "struct_item":
                sname = _name_from_field_or_child(node, src_bytes, "type_identifier")
                if sname:
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

            # ── enums ─────────────────────────────────────────────────────
            elif ntype == "enum_item":
                ename = _name_from_field_or_child(node, src_bytes, "type_identifier")
                if ename:
                    # Collect variant names as part of the signature
                    variant_nodes = [
                        c for c in _walk(node)
                        if getattr(c, "type", "") == "enum_variant"
                    ]
                    variants = []
                    for v in variant_nodes:
                        vname = _name_from_field_or_child(v, src_bytes, "identifier")
                        if vname:
                            variants.append(vname)
                    sig = f"enum {ename}" + (f"  {{ {', '.join(variants)} }}" if variants else "")
                    symbols.append(
                        Symbol(
                            name=ename,
                            kind="type",
                            file=rel,
                            line_start=node.start_point[0] + 1,  # type: ignore[attr-defined]
                            line_end=node.end_point[0] + 1,  # type: ignore[attr-defined]
                            signature=sig,
                        )
                    )

            # ── type aliases ──────────────────────────────────────────────
            elif ntype == "type_item":
                tname = _name_from_field_or_child(node, src_bytes, "type_identifier")
                if tname:
                    symbols.append(
                        Symbol(
                            name=tname,
                            kind="type",
                            file=rel,
                            line_start=node.start_point[0] + 1,  # type: ignore[attr-defined]
                            line_end=node.end_point[0] + 1,  # type: ignore[attr-defined]
                            signature=f"type {tname}",
                        )
                    )

            # ── traits ───────────────────────────────────────────────────
            elif ntype == "trait_item":
                tname = _name_from_field_or_child(node, src_bytes, "type_identifier")
                if tname:
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

            # ── consts and statics ────────────────────────────────────────
            elif ntype in ("const_item", "static_item"):
                cname = _name_from_field_or_child(node, src_bytes, "identifier")
                if cname:
                    kind_word = "const" if ntype == "const_item" else "static"
                    symbols.append(
                        Symbol(
                            name=cname,
                            kind="variable",
                            file=rel,
                            line_start=node.start_point[0] + 1,  # type: ignore[attr-defined]
                            line_end=node.end_point[0] + 1,  # type: ignore[attr-defined]
                            signature=f"{kind_word} {cname}",
                        )
                    )

            # ── macro_rules! ──────────────────────────────────────────────
            elif ntype == "macro_definition":
                mname = _name_from_field_or_child(node, src_bytes, "identifier")
                if mname:
                    symbols.append(
                        Symbol(
                            name=mname,
                            kind="other",
                            file=rel,
                            line_start=node.start_point[0] + 1,  # type: ignore[attr-defined]
                            line_end=node.end_point[0] + 1,  # type: ignore[attr-defined]
                            signature=f"macro_rules! {mname}",
                        )
                    )

            # ── mod declarations ──────────────────────────────────────────
            elif ntype == "mod_item":
                mname = _name_from_field_or_child(node, src_bytes, "identifier")
                if mname:
                    symbols.append(
                        Symbol(
                            name=mname,
                            kind="module",
                            file=rel,
                            line_start=node.start_point[0] + 1,  # type: ignore[attr-defined]
                            line_end=node.end_point[0] + 1,  # type: ignore[attr-defined]
                            signature=f"mod {mname}",
                        )
                    )

            # ── impl Trait for Type  →  Type uses Trait ───────────────────
            elif ntype == "impl_item":
                type_node = getattr(node, "child_by_field_name", lambda _: None)("type")
                trait_node = getattr(node, "child_by_field_name", lambda _: None)("trait")
                if type_node is not None and trait_node is not None:
                    type_name = _node_text(type_node, src_bytes)
                    trait_name = _node_text(trait_node, src_bytes)
                    relationships.append(
                        Relationship.model_validate(
                            {"from": type_name, "to": trait_name, "kind": "uses",
                             "file": rel, "confidence": 1.0, "evidence_tag": "EXTRACTED"}
                        )
                    )

        # ── call graph: scan all call_expression nodes ────────────────────
        for node in _walk(root):
            if getattr(node, "type", "") == "call_expression":
                fn_node = getattr(node, "child_by_field_name", lambda _: None)("function")
                if fn_node is not None:
                    callee = _node_text(fn_node, src_bytes).split("::")[-1]
                    if callee in defined_fns:
                        # find enclosing function name: walk parent chain
                        # (tree-sitter nodes have a .parent attribute)
                        enclosing = getattr(node, "parent", None)
                        while enclosing is not None:
                            if getattr(enclosing, "type", "") == "function_item":
                                caller_node = getattr(enclosing, "child_by_field_name", lambda _: None)("name")
                                if caller_node:
                                    caller = _node_text(caller_node, src_bytes)
                                    if caller != callee:
                                        relationships.append(
                                            Relationship.model_validate(
                                                {"from": caller, "to": callee, "kind": "calls",
                                                 "file": rel, "confidence": 0.9,
                                                 "evidence_tag": "EXTRACTED"}
                                            )
                                        )
                                break
                            enclosing = getattr(enclosing, "parent", None)

        return AnalysisResult(
            shard_id=rel,
            files_seen=[rel],
            entry_points=entry_points,
            symbols=symbols,
            relationships=relationships,
        )
