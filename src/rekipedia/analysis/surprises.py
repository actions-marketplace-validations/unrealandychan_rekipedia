"""Surprise connection detection (architectural smells and layer violations) for rekipedia."""
from __future__ import annotations

import collections
from pathlib import Path
from rekipedia.analysis.layer_classifier import _classify_file

LAYER_ORDER = {
    "API": 0,
    "UI": 0,
    "Service": 1,
    "Data": 2,
    "Utility": 3,
}

def detect_surprises(relationships: list[dict], symbols: list[dict], limit: int = 20) -> list[dict]:
    """Calculate composite surprise score for all relationships to identify architectural smells."""
    # Map symbol name to its file and layer
    sym_to_file = {}
    sym_to_layer = {}
    
    for s in symbols:
        if isinstance(s, dict):
            name = s.get("name", "")
            file_path = s.get("file", "")
        else:
            name = getattr(s, "name", "")
            file_path = getattr(s, "file", "")
        if name and file_path:
            sym_to_file[name] = file_path
            sym_to_layer[name] = _classify_file(file_path)

    # Calculate connectivity between modules (directories)
    module_connections = collections.Counter()
    
    # Calculate connectivity between layers
    layer_connections = collections.Counter()

    valid_rels = []
    for r in relationships:
        if isinstance(r, dict):
            frm = r.get("from_", "") or r.get("from", "")
            to = r.get("to", "")
            kind = r.get("kind", "")
        else:
            frm = getattr(r, "from_", "") or getattr(r, "from", "")
            to = getattr(r, "to", "")
            kind = getattr(r, "kind", "")
            
        if not frm or not to:
            continue
            
        # Get files
        f1 = sym_to_file.get(frm)
        f2 = sym_to_file.get(to)
        
        if not f1 or not f2 or f1 == f2:
            continue
            
        m1 = str(Path(f1).parent)
        m2 = str(Path(f2).parent)
        
        l1 = sym_to_layer.get(frm, "Utility")
        l2 = sym_to_layer.get(to, "Utility")
        
        module_connections[(m1, m2)] += 1
        layer_connections[(l1, l2)] += 1
        
        valid_rels.append({
            "from": frm,
            "to": to,
            "kind": kind,
            "file1": f1,
            "file2": f2,
            "m1": m1,
            "m2": m2,
            "l1": l1,
            "l2": l2,
        })

    surprises = []
    for r in valid_rels:
        m1, m2 = r["m1"], r["m2"]
        l1, l2 = r["l1"], r["l2"]
        
        m_conn = module_connections[(m1, m2)]
        l_conn = layer_connections[(l1, l2)]
        
        # Surprise formula components:
        # 1. Lone connection between modules
        m_surprise = 1.0 / m_conn if m_conn > 0 else 0.0
        
        # 2. Layer violation: lower-level depending on higher-level (e.g. Data -> API)
        layer_violation = False
        o1 = LAYER_ORDER.get(l1, 3)
        o2 = LAYER_ORDER.get(l2, 3)
        if o1 > o2:
            layer_violation = True
            
        # Surprise score
        surprise_score = m_surprise * 5.0
        if layer_violation:
            surprise_score += 3.0
            
        # Add penalty for circular-like layers or very rare layer connectivity
        if l_conn > 0 and l_conn < 5:
            surprise_score += 2.0
            
        surprises.append({
            "from": r["from"],
            "to": r["to"],
            "kind": r["kind"],
            "from_file": r["file1"],
            "to_file": r["file2"],
            "from_layer": l1,
            "to_layer": l2,
            "surprise_score": round(surprise_score, 2),
            "smells": ["layer-violation"] if layer_violation else ["rare-coupling"]
        })

    # Deduplicate and sort by surprise score
    seen = set()
    deduped = []
    for s in sorted(surprises, key=lambda x: x["surprise_score"], reverse=True):
        key = (s["from"], s["to"])
        if key not in seen:
            seen.add(key)
            deduped.append(s)
            
    return deduped[:limit]
