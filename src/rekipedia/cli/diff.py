"""reki diff — impact analysis for uncommitted changes."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.rule import Rule
from rich.table import Table

console = Console()

try:
    from rekipedia.analysis.impact import compute_transitive_impact as _compute_transitive_impact
    _HAS_IMPACT = True
except ImportError:  # pragma: no cover
    _compute_transitive_impact = None  # type: ignore[assignment]
    _HAS_IMPACT = False


def _get_changed_files(repo_root: Path, staged: bool, base: str | None) -> list[str]:
    """Return list of changed file paths relative to repo_root."""
    def _run(extra_flags: list[str]) -> list[str]:
        cmd = ["git", "diff", "--name-only"] + extra_flags
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_root)
        if result.returncode != 0:
            return []
        return [f.strip() for f in result.stdout.splitlines() if f.strip()]

    if base:
        return _run([base, "HEAD"])
    if staged:
        return _run(["--cached"])
    # Neither --staged nor --base: union of staged + unstaged
    staged_files = _run(["--cached"])
    unstaged_files = _run([])
    seen: set[str] = set()
    result: list[str] = []
    for f in staged_files + unstaged_files:
        if f not in seen:
            seen.add(f)
            result.append(f)
    return result


def _risk_tier(total_affected: int) -> tuple[str, str]:
    """Return (label, emoji) for the risk tier."""
    if total_affected >= 5:
        return "HIGH", "🔴"
    if total_affected >= 2:
        return "MEDIUM", "🟡"
    return "LOW", "🟢"


# ── graph-diff helpers ────────────────────────────────────────────────────────

def _edge_key(rel: dict[str, Any]) -> tuple[str, str, str]:
    """Canonical (from, to, kind) key for a relationship dict."""
    return (
        rel.get("from_") or rel.get("from") or "",
        rel.get("to") or "",
        rel.get("kind") or "",
    )


def compute_graph_diff(
    old_rels: list[dict[str, Any]],
    new_rels: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare two relationship snapshots and return an edge-level diff.

    Args:
        old_rels: Relationships from the previous scan run.
        new_rels: Relationships from the current (latest) scan run.

    Returns:
        Dict with keys:
            added   — list of edges present in new but not old
            removed — list of edges present in old but not new
            unchanged_count — number of edges present in both
            summary — human-readable string
    """
    old_keys = {_edge_key(r): r for r in old_rels}
    new_keys = {_edge_key(r): r for r in new_rels}

    added_keys   = set(new_keys) - set(old_keys)
    removed_keys = set(old_keys) - set(new_keys)
    unchanged    = len(set(old_keys) & set(new_keys))

    added   = [new_keys[k] for k in sorted(added_keys)]
    removed = [old_keys[k] for k in sorted(removed_keys)]

    summary = (
        f"+{len(added)} edges added, -{len(removed)} edges removed, "
        f"{unchanged} unchanged"
    )
    return {
        "added":           added,
        "removed":         removed,
        "unchanged_count": unchanged,
        "summary":         summary,
    }


def _print_graph_diff(diff: dict[str, Any]) -> None:
    """Render graph diff to terminal in a Rich table."""
    added   = diff["added"]
    removed = diff["removed"]

    console.print(f"\n📊  Graph Diff — {diff['summary']}\n")

    if added:
        t = Table(title=f"➕ Added edges ({len(added)})", show_lines=False)
        t.add_column("From",  style="green")
        t.add_column("→ To",  style="green")
        t.add_column("Kind",  style="dim")
        for e in added[:50]:
            t.add_row(
                e.get("from_") or e.get("from") or "",
                e.get("to") or "",
                e.get("kind") or "",
            )
        console.print(t)
        if len(added) > 50:
            console.print(f"  ... and {len(added) - 50} more added edges")

    if removed:
        t = Table(title=f"➖ Removed edges ({len(removed)})", show_lines=False)
        t.add_column("From",  style="red")
        t.add_column("→ To",  style="red")
        t.add_column("Kind",  style="dim")
        for e in removed[:50]:
            t.add_row(
                e.get("from_") or e.get("from") or "",
                e.get("to") or "",
                e.get("kind") or "",
            )
        console.print(t)
        if len(removed) > 50:
            console.print(f"  ... and {len(removed) - 50} more removed edges")

    if not added and not removed:
        console.print("  ✅ No graph changes — edge set identical between runs")


@click.command("diff")
@click.argument("repo", default=".", metavar="REPO")
@click.option("--staged", is_flag=True, help="Staged changes only")
@click.option("--base", default=None, help="Compare against this git ref (e.g. HEAD~3)")
@click.option(
    "--format", "fmt",
    default="text",
    type=click.Choice(["text", "json"]),
    help="Output format",
)
@click.option(
    "--graph-diff", "graph_diff", is_flag=True, default=False,
    help="Show edge-level graph diff between the last two scan runs.",
)
def diff_cmd(repo: str, staged: bool, base: str | None, fmt: str, graph_diff: bool) -> None:
    """Show impact analysis for uncommitted changes.

    With --graph-diff: compare the relationship graph between the last two
    scan runs and display added/removed edges.
    """
    repo_path = Path(repo).resolve()

    # Check git repo
    git_check = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        capture_output=True, text=True, cwd=repo_path
    )
    if git_check.returncode != 0:
        console.print("❌ Not a git repository")
        raise SystemExit(1)

    # Check store
    db_path = repo_path / ".rekipedia" / "store.db"
    if not db_path.exists():
        alt = repo_path / ".rekipedia" / "rekipedia.db"
        if alt.exists():
            db_path = alt

    if not db_path.exists():
        console.print("❌ No scan found — run 'reki scan .' first")
        raise SystemExit(1)

    from rekipedia.storage.sqlite_store import SqliteStore

    # ── graph diff mode ──────────────────────────────────────────────────
    if graph_diff:
        with SqliteStore(db_path) as store:
            latest, previous = store.get_two_latest_run_ids(str(repo_path))
            if not latest:
                console.print("❌ No scan runs found — run 'reki scan .' first")
                raise SystemExit(1)
            if not previous:
                console.print("⚠️  Only one scan run found — need at least two runs to diff")
                console.print(f"   Latest run: {latest}")
                raise SystemExit(0)
            new_rels = store.get_relationships_for_run(latest)
            old_rels = store.get_relationships_for_run(previous)

        diff = compute_graph_diff(old_rels, new_rels)

        if fmt == "json":
            click.echo(json.dumps(diff, indent=2))
            return

        _print_graph_diff(diff)
        return

    # ── file impact mode (default) ───────────────────────────────────────
    # Get changed files (filter out .rekipedia/ generated output)
    changed_files = [
        f for f in _get_changed_files(repo_path, staged, base)
        if not f.startswith(".rekipedia/")
    ]
    if not changed_files:
        console.print("✅ No changes detected")
        raise SystemExit(0)

    has_impact = _compute_transitive_impact is not None

    # Load store
    store = SqliteStore(db_path)
    with store:
        run_id = store.get_latest_run_id(str(repo_path))
        if not run_id:
            console.print("❌ No scan found — run 'reki scan .' first")
            raise SystemExit(1)
        all_symbols = store.get_all_symbols(run_id)
        if has_impact:
            all_relationships = store.get_all_relationships(run_id)

    # Index symbols by file
    # scan_symbols columns: run_id(0), name(1), kind(2), file(3), ...
    sym_by_file: dict[str, list] = {}
    for s in all_symbols:
        if isinstance(s, dict):
            f = s.get("file")
            name = s.get("name")
        elif hasattr(s, "keys"):  # sqlite3.Row
            f = s["file"]
            name = s["name"]
        else:  # tuple
            name = s[1] if len(s) > 1 else None
            f = s[3] if len(s) > 3 else None
        if f and name:
            sym_by_file.setdefault(f, []).append(name)

    # Compute impact per file/symbol
    results: list[dict] = []
    total_affected_all: set[str] = set()

    for changed_file in changed_files:
        file_symbols = sym_by_file.get(changed_file, [])
        if not file_symbols:
            results.append({
                "file": changed_file,
                "symbol": None,
                "risk": "LOW",
                "total_affected": 0,
                "affected_files": [],
                "callers": [],
            })
            continue

        if not has_impact:
            # Fallback: just list symbols without impact
            for sym in file_symbols:
                results.append({
                    "file": changed_file,
                    "symbol": sym,
                    "risk": "LOW",
                    "total_affected": 0,
                    "affected_files": [],
                    "callers": [],
                })
            continue

        for sym in file_symbols:
            impact = _compute_transitive_impact(
                sym, all_relationships, all_symbols, depth=5, direction="both"
            )
            callers = impact.get("results", impact.get("affected_symbols", []))
            if isinstance(callers, list) and callers and isinstance(callers[0], str):
                # Old format: list of symbol names
                callers = [{"symbol": c, "depth": 0, "file": None} for c in callers]
            total = len(callers)
            affected_files = list({c["file"] for c in callers if isinstance(c, dict) and c.get("file")})
            for af in affected_files:
                total_affected_all.add(af)
            risk_label, _ = _risk_tier(total)
            results.append({
                "file": changed_file,
                "symbol": sym,
                "risk": risk_label,
                "total_affected": total,
                "affected_files": affected_files,
                "callers": callers,
            })

    # Sort by total_affected descending
    results.sort(key=lambda x: x["total_affected"], reverse=True)

    if fmt == "json":
        output = {
            "repo": str(repo_path),
            "changed_files": changed_files,
            "total_affected_symbols": len(total_affected_all),
            "results": results,
        }
        click.echo(json.dumps(output, indent=2))
        return

    # Text output
    total_sym_count = len(results)
    console.print("\n🔍  Diff Impact Analysis")
    console.print(f"{len(changed_files)} changed files · {total_sym_count} symbols affected\n")

    # Group by file
    by_file: dict[str, list[dict]] = {}
    for r in results:
        by_file.setdefault(r["file"], []).append(r)

    for filepath, file_results in by_file.items():
        console.print(Rule(f" {filepath} ", style="bold"))
        for r in file_results:
            sym = r["symbol"] or filepath
            total = r["total_affected"]
            risk_label, emoji = _risk_tier(total)
            callers = r["callers"]
            caller_word = "caller" if total == 1 else "callers"
            console.print(f"  ✏️  [bold]{sym}[/bold]   {emoji} {risk_label} IMPACT · {total} {caller_word}")
            for c in callers[:3]:
                if isinstance(c, dict):
                    sym_name = c.get("symbol", "")
                    depth = c.get("depth", "?")
                    f = c.get("file") or ""
                    console.print(f"      {sym_name} (depth {depth})" + (f" · {f}" if f else ""))
            if len(callers) > 3:
                console.print(f"      ... and {len(callers) - 3} more")
            console.print()
