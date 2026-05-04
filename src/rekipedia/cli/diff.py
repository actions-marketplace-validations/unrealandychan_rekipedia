"""rekipedia diff command — commit-level knowledge diff."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import click


def _run_git(args: list[str], cwd: str) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def _load_symbols_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return data.get("symbols", [])


def _symbols_from_store(store_path: Path, run_id: str | None = None) -> list[dict[str, Any]]:
    """Load symbols from SQLite store if available."""
    if not store_path.exists():
        return []
    try:
        import sqlite3
        conn = sqlite3.connect(str(store_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if run_id is None:
            cur.execute("SELECT id FROM runs ORDER BY created_at DESC LIMIT 1")
            row = cur.fetchone()
            if not row:
                conn.close()
                return []
            run_id = row[0]
        cur.execute("SELECT * FROM symbols WHERE run_id = ?", (run_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _relationships_from_store(store_path: Path, run_id: str | None = None) -> list[dict[str, Any]]:
    if not store_path.exists():
        return []
    try:
        import sqlite3
        conn = sqlite3.connect(str(store_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if run_id is None:
            cur.execute("SELECT id FROM runs ORDER BY created_at DESC LIMIT 1")
            row = cur.fetchone()
            if not row:
                conn.close()
                return []
            run_id = row[0]
        cur.execute("SELECT * FROM relationships WHERE run_id = ?", (run_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _format_diff_md(
    added: list[str],
    removed: list[str],
    changed: list[str],
    added_rels: list[str],
    removed_rels: list[str],
    changed_files: list[str],
    from_ref: str,
    to_ref: str,
) -> str:
    lines = [
        f"# Knowledge Diff: `{from_ref}` → `{to_ref}`",
        "",
    ]

    if changed_files:
        lines += ["## Changed Files", ""]
        for f in changed_files:
            lines.append(f"- `{f}`")
        lines.append("")

    if not added and not removed and not changed and not added_rels and not removed_rels:
        lines += ["## No Changes", "", "_No symbol or relationship changes detected._", ""]
        return "\n".join(lines)

    if added:
        lines += ["## Added Symbols", ""]
        for s in added:
            lines.append(f"+ `{s}`")
        lines.append("")

    if removed:
        lines += ["## Removed Symbols", ""]
        for s in removed:
            lines.append(f"- `{s}`")
        lines.append("")

    if changed:
        lines += ["## Changed Symbols", ""]
        for s in changed:
            lines.append(f"~ `{s}`")
        lines.append("")

    if added_rels:
        lines += ["## Added Relationships", ""]
        for r in added_rels:
            lines.append(f"+ {r}")
        lines.append("")

    if removed_rels:
        lines += ["## Removed Relationships", ""]
        for r in removed_rels:
            lines.append(f"- {r}")
        lines.append("")

    return "\n".join(lines)


def _format_diff_text(
    added: list[str],
    removed: list[str],
    changed: list[str],
    added_rels: list[str],
    removed_rels: list[str],
    changed_files: list[str],
    from_ref: str,
    to_ref: str,
) -> str:
    lines = [f"Knowledge Diff: {from_ref} -> {to_ref}", "=" * 40]

    if changed_files:
        lines += ["", "Changed Files:"]
        for f in changed_files:
            lines.append(f"  {f}")

    if not added and not removed and not changed and not added_rels and not removed_rels:
        lines += ["", "No changes detected."]
        return "\n".join(lines)

    if added:
        lines += ["", "Added Symbols:"]
        for s in added:
            lines.append(f"  + {s}")
    if removed:
        lines += ["", "Removed Symbols:"]
        for s in removed:
            lines.append(f"  - {s}")
    if changed:
        lines += ["", "Changed Symbols:"]
        for s in changed:
            lines.append(f"  ~ {s}")
    if added_rels:
        lines += ["", "Added Relationships:"]
        for r in added_rels:
            lines.append(f"  + {r}")
    if removed_rels:
        lines += ["", "Removed Relationships:"]
        for r in removed_rels:
            lines.append(f"  - {r}")

    return "\n".join(lines)


def _symbol_key(sym: dict[str, Any]) -> str:
    return sym.get("name") or sym.get("qualified_name") or str(sym.get("id", ""))


def _rel_key(rel: dict[str, Any]) -> str:
    return f"{rel.get('from_symbol', rel.get('source', ''))} -> {rel.get('to_symbol', rel.get('target', ''))} [{rel.get('kind', rel.get('type', ''))}]"


@click.command("diff")
@click.option("--repo", default=".", show_default=True, help="Path to the git repository")
@click.option("--from-ref", default="HEAD~1", show_default=True, help="Starting git ref")
@click.option("--to-ref", default="HEAD", show_default=True, help="Ending git ref")
@click.option("--output-dir", default=None, help="Directory to write diff output (default: .rekipedia)")
@click.option("--format", "fmt", default="md", type=click.Choice(["md", "text"]), show_default=True, help="Output format")
def diff_cmd(repo: str, from_ref: str, to_ref: str, output_dir: str | None, fmt: str) -> None:
    """Show a commit-level knowledge diff between two refs."""
    repo_path = Path(repo).resolve()
    reki_dir = Path(output_dir) if output_dir else repo_path / ".rekipedia"
    store_path = reki_dir / "store.db"
    exports_dir = reki_dir / "exports"
    symbols_json = exports_dir / "symbols.json"

    # Get changed files between refs
    changed_files: list[str] = []
    diff_output = _run_git(["diff", "--name-only", from_ref, to_ref], str(repo_path))
    if diff_output:
        changed_files = [line for line in diff_output.splitlines() if line.strip()]

    # Load current symbols
    current_symbols = _load_symbols_json(symbols_json)
    if not current_symbols:
        current_symbols = _symbols_from_store(store_path)

    current_rels = _relationships_from_store(store_path)

    # Determine symbols in changed files
    changed_file_set = set(changed_files)

    def in_changed_files(sym: dict[str, Any]) -> bool:
        sym_file = sym.get("file", sym.get("source_file", ""))
        if not sym_file:
            return False
        # normalize
        sym_file = sym_file.lstrip("/")
        return any(sym_file.endswith(cf) or cf.endswith(sym_file) for cf in changed_file_set)

    # If store is empty or no previous snapshot — treat all as added
    if not current_symbols:
        click.echo("No symbols found. Run `rekipedia scan` first.")
        content = _format_diff_md([], [], [], [], [], changed_files, from_ref, to_ref) if fmt == "md" \
            else _format_diff_text([], [], [], [], [], changed_files, from_ref, to_ref)
        _output(content, reki_dir, fmt)
        return

    # Try to get snapshot from previous ref using git show
    prev_symbols_raw = _run_git(
        ["show", f"{from_ref}:.rekipedia/exports/symbols.json"], str(repo_path)
    )
    prev_symbols: list[dict[str, Any]] = []
    if prev_symbols_raw:
        try:
            parsed = json.loads(prev_symbols_raw)
            prev_symbols = parsed if isinstance(parsed, list) else parsed.get("symbols", [])
        except json.JSONDecodeError:
            prev_symbols = []

    if not prev_symbols:
        # No previous snapshot — all current symbols are "added"
        added = [_symbol_key(s) for s in current_symbols]
        content = _format_diff_md(added, [], [], [], [], changed_files, from_ref, to_ref) if fmt == "md" \
            else _format_diff_text(added, [], [], [], [], changed_files, from_ref, to_ref)
        _output(content, reki_dir, fmt)
        return

    # Compare snapshots
    prev_map = {_symbol_key(s): s for s in prev_symbols}
    curr_map = {_symbol_key(s): s for s in current_symbols}

    added = [k for k in curr_map if k not in prev_map]
    removed = [k for k in prev_map if k not in curr_map]
    changed = []
    for k in curr_map:
        if k in prev_map:
            # Check if file is in changed set
            if changed_file_set and in_changed_files(curr_map[k]):
                changed.append(k)

    # Relationship diff (simple)
    prev_rels_raw = _run_git(
        ["show", f"{from_ref}:.rekipedia/exports/relationships.json"], str(repo_path)
    )
    prev_rels: list[dict[str, Any]] = []
    if prev_rels_raw:
        try:
            parsed = json.loads(prev_rels_raw)
            prev_rels = parsed if isinstance(parsed, list) else parsed.get("relationships", [])
        except json.JSONDecodeError:
            prev_rels = []

    prev_rel_keys = {_rel_key(r) for r in prev_rels}
    curr_rel_keys = {_rel_key(r) for r in current_rels}
    added_rels = sorted(curr_rel_keys - prev_rel_keys)
    removed_rels = sorted(prev_rel_keys - curr_rel_keys)

    content = _format_diff_md(added, removed, changed, added_rels, removed_rels, changed_files, from_ref, to_ref) if fmt == "md" \
        else _format_diff_text(added, removed, changed, added_rels, removed_rels, changed_files, from_ref, to_ref)

    _output(content, reki_dir, fmt)


def _output(content: str, reki_dir: Path, fmt: str) -> None:
    ext = "md" if fmt == "md" else "txt"
    reki_dir.mkdir(parents=True, exist_ok=True)
    out_file = reki_dir / f"diff.{ext}"
    out_file.write_text(content)
    click.echo(content)
    click.echo(f"\n[diff written to {out_file}]", err=True)
