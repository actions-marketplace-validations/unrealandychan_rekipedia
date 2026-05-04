"""Snapshot serialisation for graph diff."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from rekipedia.models.contracts import AnalysisResult

SNAPSHOT_DIR_NAME = ".rekipedia/snapshots"

def save_snapshot(combined: AnalysisResult, output_dir: Path) -> Path:
    """Serialise combined into a timestamped JSON snapshot."""
    snap_dir = output_dir / SNAPSHOT_DIR_NAME
    snap_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    snap_path = snap_dir / f"{ts}.json"
    data = {
        "timestamp": ts,
        "symbols": [s.model_dump() for s in combined.symbols],
        "relationships": [r.model_dump(by_alias=True) for r in combined.relationships],
    }
    snap_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return snap_path

def list_snapshots(output_dir: Path) -> list[Path]:
    snap_dir = output_dir / SNAPSHOT_DIR_NAME
    if not snap_dir.exists():
        return []
    return sorted(snap_dir.glob("*.json"))

def load_snapshot(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def diff_snapshots(snap_a: dict, snap_b: dict) -> dict:
    """Compute diff between two snapshots. Returns added/removed/modified for symbols and relationships."""
    def sym_key(s): return s["name"]
    def rel_key(r): return (r.get("from_") or r.get("from", ""), r.get("to", ""), r.get("kind", ""))

    syms_a = {sym_key(s): s for s in snap_a.get("symbols", [])}
    syms_b = {sym_key(s): s for s in snap_b.get("symbols", [])}
    rels_a = {rel_key(r): r for r in snap_a.get("relationships", [])}
    rels_b = {rel_key(r): r for r in snap_b.get("relationships", [])}

    added_syms = [syms_b[k] for k in syms_b if k not in syms_a]
    removed_syms = [syms_a[k] for k in syms_a if k not in syms_b]
    modified_syms = [syms_b[k] for k in syms_a if k in syms_b and syms_a[k] != syms_b[k]]

    added_rels = [rels_b[k] for k in rels_b if k not in rels_a]
    removed_rels = [rels_a[k] for k in rels_a if k not in rels_b]

    return {
        "symbols": {"added": added_syms, "removed": removed_syms, "modified": modified_syms},
        "relationships": {"added": added_rels, "removed": removed_rels},
        "summary": {
            "symbols_added": len(added_syms),
            "symbols_removed": len(removed_syms),
            "symbols_modified": len(modified_syms),
            "relationships_added": len(added_rels),
            "relationships_removed": len(removed_rels),
        },
    }
