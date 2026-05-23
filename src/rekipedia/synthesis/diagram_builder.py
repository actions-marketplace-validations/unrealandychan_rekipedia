"""Build Mermaid diagrams from relationship data."""
from __future__ import annotations

import re


class DiagramBuilder:
    """Generate Mermaid diagrams from relationship rows."""

    def build(self, relationships: list, entry_points: list[str] | None = None) -> dict[str, tuple[str, str]]:
        """Return {name: (diagram_type, mermaid_content)}."""
        results: dict[str, tuple[str, str]] = {}
        if not relationships:
            return results
        rows = [_to_dict(r) for r in relationships]
        results["module-graph"] = ("flowchart", _build_module_graph(rows, entry_points=entry_points))
        results["class-hierarchy"] = ("classDiagram", _build_class_hierarchy(rows))
        return results


# ── diagram builders ─────────────────────────────────────────────────

def _build_module_graph(rows: list[dict], entry_points: list[str] | None = None) -> str:
    """flowchart LR showing top-level MODULE relationships (not individual symbols).

    Groups files by top-level package/directory so the diagram shows
    high-level architecture instead of a symbol soup.
    """
    _EXTERNAL_PREFIXES = (
        "os", "sys", "re", "io", "json", "time", "math", "typing", "pathlib",
        "collections", "itertools", "functools", "dataclasses", "enum", "abc",
        "logging", "threading", "subprocess", "asyncio", "contextlib", "copy",
        "hashlib", "base64", "uuid", "random", "datetime", "string", "struct",
        "importlib", "inspect", "warnings", "weakref", "traceback", "textwrap",
        # popular third-party
        "fastapi", "pydantic", "sqlalchemy", "django", "flask", "requests",
        "httpx", "aiohttp", "numpy", "pandas", "torch", "sklearn", "openai",
        "boto3", "celery", "redis", "pytest", "click", "typer", "rich",
        "starlette", "uvicorn", "gunicorn", "alembic", "litellm", "faiss",
        "tree_sitter", "pathspec", "pyfiglet", "markdown", "certifi",
        # Go stdlib
        "fmt", "strings", "strconv", "bytes", "errors", "sort", "sync",
        "bufio", "reflect", "unicode", "flag", "net", "log", "context",
        "runtime", "encoding", "crypto", "regexp", "path/filepath", "http",
        "grpc", "testing", "os/exec", "io/fs",
    )

    def _top_module(name: str) -> str:
        """Extract the top-level module/package name from a file path or import."""
        # File path: src/rekipedia/cli/scan.py  → src/rekipedia/cli  → rekipedia.cli
        # Import: rekipedia.extractors.go_extractor  → rekipedia.extractors
        # Go import: github.com/user/repo/internal/foo  → internal/foo
        if "/" in name:
            parts = name.split("/")
            # For Python src layout: src/pkg → pkg
            if parts[0] == "src" and len(parts) > 1:
                parts = parts[1:]
            # Return top two components for depth
            pkg = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
            return pkg.replace(".py", "").replace(".go", "").replace(".ts", "")
        elif "." in name:
            parts = name.split(".")
            return ".".join(parts[:2]) if len(parts) > 1 else parts[0]
        return name

    # Build module-level edges (deduplicated)
    module_import_edges: set[tuple[str, str]] = set()
    module_call_edges: set[tuple[str, str]] = set()
    module_inherit_edges: set[tuple[str, str]] = set()

    for r in rows:
        frm = r.get("from_") or r.get("from") or ""
        to = r.get("to") or ""
        kind = r.get("kind") or ""
        if not frm or not to:
            continue

        is_external = any(
            to == p or to.startswith(p + ".") or to.startswith(p + "/")
            for p in _EXTERNAL_PREFIXES
        )
        if is_external:
            continue

        frm_mod = _top_module(frm)
        to_mod = _top_module(to)
        if frm_mod == to_mod:
            continue  # Skip intra-module edges

        if kind in ("import", "imports"):
            module_import_edges.add((frm_mod, to_mod))
        elif kind in ("call", "calls"):
            module_call_edges.add((frm_mod, to_mod))
        elif kind in ("inherits", "inherit"):
            module_inherit_edges.add((frm_mod, to_mod))

    all_nodes: set[str] = set()
    for a, b in module_import_edges | module_call_edges | module_inherit_edges:
        all_nodes.add(a)
        all_nodes.add(b)

    if not all_nodes:
        return "flowchart LR\n  A[No internal relationships detected]"

    # Limit total nodes to keep diagram readable
    _MAX_NODES = 20
    if len(all_nodes) > _MAX_NODES:
        # Keep nodes with most connections
        node_degree: dict[str, int] = {}
        for a, b in module_import_edges | module_call_edges | module_inherit_edges:
            node_degree[a] = node_degree.get(a, 0) + 1
            node_degree[b] = node_degree.get(b, 0) + 1
        top_nodes = {n for n, _ in sorted(node_degree.items(), key=lambda x: -x[1])[:_MAX_NODES]}
        all_nodes = top_nodes
        module_import_edges = {(a, b) for a, b in module_import_edges if a in top_nodes and b in top_nodes}
        module_call_edges = {(a, b) for a, b in module_call_edges if a in top_nodes and b in top_nodes}
        module_inherit_edges = {(a, b) for a, b in module_inherit_edges if a in top_nodes and b in top_nodes}

    def node_id(name: str) -> str:
        return re.sub(r"[^A-Za-z0-9_]", "_", name)

    def node_label(name: str) -> str:
        label = name.split("/")[-1].split(".")[-1]
        return label or name

    lines = ["flowchart LR"]

    defined: set[str] = set()
    for name in sorted(all_nodes):
        nid = node_id(name)
        if nid not in defined:
            label = node_label(name)
            lines.append(f'  {nid}["{label}"]')
            defined.add(nid)

    lines.append("")

    for frm, to in sorted(module_import_edges)[:30]:
        lines.append(f"  {node_id(frm)} -->|imports| {node_id(to)}")

    for frm, to in sorted(module_call_edges)[:15]:
        lines.append(f"  {node_id(frm)} -.->|calls| {node_id(to)}")

    for child, parent in sorted(module_inherit_edges)[:10]:
        lines.append(f"  {node_id(child)} -->|inherits| {node_id(parent)}")

    lines.append("")

    # Style entry-point modules in gold
    for ep in (entry_points or []):
        ep_mod = _top_module(ep)
        nid = node_id(ep_mod)
        if nid in defined:
            lines.append(f"  style {nid} fill:#f4a700,stroke:#c47d00,color:#000")

    return "\n".join(lines)


def _build_class_hierarchy(rows: list[dict]) -> str:
    """classDiagram showing inheritance relationships."""
    inheritances: list[tuple[str, str]] = []

    for r in rows:
        if r.get("kind") == "inherits":
            frm = r.get("from_") or r.get("from") or ""
            to = r.get("to") or ""
            if frm and to:
                inheritances.append((_sanitise_class(frm), _sanitise_class(to)))

    if not inheritances:
        return "classDiagram\n  note \"No inheritance relationships detected\""

    lines = ["classDiagram"]
    for child, parent in inheritances[:20]:
        lines.append(f"  {parent} <|-- {child}")
    return "\n".join(lines)


# ── helpers ──────────────────────────────────────────────────────────

def _to_dict(row) -> dict:
    if isinstance(row, dict):
        return row
    try:
        return dict(row)
    except Exception:
        return {}


def _sanitise(name: str) -> str:
    """Convert a file path to a valid Mermaid node id."""
    # Replace non-alphanumeric characters
    s = re.sub(r"[^A-Za-z0-9_]", "_", name)
    # Ensure doesn't start with digit
    if s and s[0].isdigit():
        s = "_" + s
    return s or "unknown"


def _sanitise_class(name: str) -> str:
    """Strip fully-qualified prefix for class names."""
    return re.sub(r"[^A-Za-z0-9_]", "_", name.split(".")[-1]) or "Unknown"
