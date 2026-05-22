"""
onboard.py — Generate an onboarding guide for new developers.

Builds a structured guide from existing rekipedia data:
- Project overview (from README if found, else from most-connected nodes)
- Architecture summary (from domain layer classification)
- Getting-started steps (entry point files, test commands, build commands)
- Key modules to read first (hub nodes by connectivity)
- Common patterns (top symbol kinds)
- Links to generated wiki pages
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def build_onboard_guide(store_path: Path, repo_root: Path) -> dict:
    """
    Returns:
    {
        "repo": str,
        "generated_at": "ISO",
        "overview": str,  # first paragraph of README or "N files, N symbols"
        "getting_started": [
            {"step": 1, "title": "...", "cmd": "..."},
            ...
        ],
        "key_modules": [
            {"path": "...", "description": "Top module", "symbols": [...]}
        ],
        "architecture": {
            "layers": {"Service": 8, "Utility": 29, ...}
        },
        "patterns": [
            {"kind": "function", "count": 142},
        ],
        "wiki_dir": str  # path to .rekipedia/wiki/ if it exists
    }
    """
    from rekipedia.analysis.domain import _classify_file

    con = sqlite3.connect(str(store_path))
    con.row_factory = sqlite3.Row
    try:
        # Get latest run_id
        row = con.execute(
            "SELECT run_id FROM scan_runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        run_id = row["run_id"] if row else None

        symbol_count = 0
        file_count = 0
        key_modules: list[dict] = []
        patterns: list[dict] = []
        layers: dict[str, int] = {}

        if run_id:
            symbol_count = con.execute(
                "SELECT COUNT(*) FROM scan_symbols WHERE run_id=?", (run_id,)
            ).fetchone()[0]
            file_count = con.execute(
                "SELECT COUNT(DISTINCT file) FROM scan_symbols WHERE run_id=?", (run_id,)
            ).fetchone()[0]

            # Top 5 hub modules
            rows = con.execute(
                "SELECT file, COUNT(*) as cnt FROM scan_symbols WHERE run_id=? "
                "GROUP BY file ORDER BY cnt DESC LIMIT 5",
                (run_id,),
            ).fetchall()
            for r in rows:
                syms = [
                    s[0]
                    for s in con.execute(
                        "SELECT name FROM scan_symbols WHERE run_id=? AND file=? LIMIT 5",
                        (run_id, r["file"]),
                    ).fetchall()
                ]
                key_modules.append(
                    {
                        "path": r["file"],
                        "description": "Top module",
                        "symbols": syms,
                        "count": r["cnt"],
                    }
                )

            # Pattern counts
            rows = con.execute(
                "SELECT kind, COUNT(*) as cnt FROM scan_symbols WHERE run_id=? "
                "GROUP BY kind ORDER BY cnt DESC",
                (run_id,),
            ).fetchall()
            patterns = [{"kind": r["kind"], "count": r["cnt"]} for r in rows]

            # Layer classification
            files = con.execute(
                "SELECT DISTINCT file FROM scan_symbols WHERE run_id=?", (run_id,)
            ).fetchall()
            for f in files:
                layer = _classify_file(f["file"])
                layers[layer] = layers.get(layer, 0) + 1
    finally:
        con.close()

    # Overview: try README
    overview = f"{file_count} files, {symbol_count} symbols"
    for readme_name in ("README.md", "README.rst", "README.txt", "readme.md"):
        readme = repo_root / readme_name
        if readme.exists():
            text = readme.read_text(errors="replace")
            paragraphs = text.split("\n\n")
            for para in paragraphs:
                stripped = para.strip()
                # Skip headings-only paragraphs
                lines = [l for l in stripped.splitlines() if not l.startswith("#") and l.strip()]
                if lines:
                    overview = " ".join(lines)
                    break
            break

    # Getting-started steps
    steps: list[dict] = []
    step_num = 1

    # Install
    if (repo_root / "pyproject.toml").exists() or (repo_root / "setup.py").exists():
        steps.append({"step": step_num, "title": "Install deps", "cmd": "pip install -e ."})
        step_num += 1
    elif (repo_root / "package.json").exists():
        steps.append({"step": step_num, "title": "Install deps", "cmd": "npm install"})
        step_num += 1
    elif (repo_root / "Cargo.toml").exists():
        steps.append({"step": step_num, "title": "Build", "cmd": "cargo build"})
        step_num += 1
    elif (repo_root / "go.mod").exists():
        steps.append({"step": step_num, "title": "Build", "cmd": "go build ./..."})
        step_num += 1

    # Test
    if (repo_root / "pytest.ini").exists() or (repo_root / "pyproject.toml").exists():
        steps.append({"step": step_num, "title": "Run tests", "cmd": "pytest"})
        step_num += 1
    elif (repo_root / "package.json").exists():
        steps.append({"step": step_num, "title": "Run tests", "cmd": "npm test"})
        step_num += 1
    elif (repo_root / "Cargo.toml").exists():
        steps.append({"step": step_num, "title": "Run tests", "cmd": "cargo test"})
        step_num += 1

    steps.append({"step": step_num, "title": "Scan codebase", "cmd": "reki scan ."})
    step_num += 1
    steps.append({"step": step_num, "title": "Explore", "cmd": 'reki ask "how does X work?"'})
    step_num += 1
    steps.append({"step": step_num, "title": "Tour", "cmd": "reki tour ."})

    # Wiki dir
    wiki_dir = repo_root / ".rekipedia" / "wiki"
    wiki_dir_str = str(wiki_dir) if wiki_dir.exists() else None

    return {
        "repo": str(repo_root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overview": overview,
        "getting_started": steps,
        "key_modules": key_modules,
        "architecture": {"layers": layers},
        "patterns": patterns,
        "wiki_dir": wiki_dir_str,
        "_counts": {"files": file_count, "symbols": symbol_count},
    }
