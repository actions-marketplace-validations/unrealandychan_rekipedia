"""Business domain layer classification for rekipedia."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


_LAYERS = ("API", "Service", "Data", "UI", "Utility")


def _classify_file(path: str) -> str:
    p = path.lower()
    stem = Path(p).stem

    # UI layer
    if any(x in p for x in ['template', 'component', 'frontend', 'ui/', 'views/', 'pages/', 'static/']):
        return 'UI'
    if Path(p).suffix in {'.html', '.tsx', '.jsx', '.vue', '.svelte', '.css', '.scss'}:
        return 'UI'

    # API layer
    if any(x in p for x in ['route', 'handler', 'controller', 'endpoint', 'api/', 'rest/', 'graphql/']):
        return 'API'
    if any(x in stem for x in ['route', 'handler', 'controller', 'endpoint', 'view']):
        return 'API'

    # Data layer
    if any(x in p for x in ['model', 'schema', 'migration', 'db/', 'database/', 'repository', 'dao/', 'orm/']):
        return 'Data'
    if any(x in stem for x in ['model', 'schema', 'migration', 'entity', 'repository']):
        return 'Data'

    # Service layer
    if any(x in p for x in ['service', 'manager', 'processor', 'orchestrat', 'workflow', 'business/']):
        return 'Service'
    if any(x in stem for x in ['service', 'manager', 'processor', 'orchestrat', 'workflow']):
        return 'Service'

    # Utility (catch-all for common util patterns)
    if any(x in p for x in ['util', 'helper', 'constant', 'config', 'setting', 'common/', 'shared/', 'lib/']):
        return 'Utility'

    return 'Utility'  # fallback


def classify_domain(store, run_id: str, repo_root) -> dict:
    """Classify codebase files into business domain layers."""
    symbols = store.get_all_symbols(run_id)
    relationships = store.get_all_relationships(run_id)

    # Build file -> symbols mapping
    file_symbols: dict[str, list[str]] = defaultdict(list)
    sym_file: dict[str, str] = {}
    for s in symbols:
        name = s.name if hasattr(s, "name") else s.get("name", "")
        file = s.file if hasattr(s, "file") else s.get("file", "")
        if file:
            file_symbols[file].append(name)
            sym_file[name] = file

    # Classify each file
    file_layer: dict[str, str] = {}
    for file in file_symbols:
        file_layer[file] = _classify_file(file)

    # Build layer data
    layer_files: dict[str, list[str]] = defaultdict(list)
    layer_syms: dict[str, list[str]] = defaultdict(list)
    for file, layer in file_layer.items():
        layer_files[layer].append(file)
        layer_syms[layer].extend(file_symbols[file])

    layers_result: dict[str, dict] = {}
    for layer in _LAYERS:
        files = sorted(layer_files.get(layer, []))
        syms = layer_syms.get(layer, [])
        if files:
            layers_result[layer] = {
                "files": files,
                "symbol_count": len(syms),
                "key_symbols": syms[:5],
            }

    # Build inter-layer dependency graph
    dep_counts: dict[tuple[str, str], int] = defaultdict(int)
    for rel in relationships:
        kind = rel.kind if hasattr(rel, "kind") else rel.get("kind", "")
        if kind not in ("imports", "calls"):
            continue
        frm = rel.from_ if hasattr(rel, "from_") else rel.get("from_", "") or rel.get("from", "")
        to = rel.to if hasattr(rel, "to") else rel.get("to", "")
        from_file = sym_file.get(frm, "")
        to_file = sym_file.get(to, "")
        if not from_file or not to_file:
            continue
        from_layer = file_layer.get(from_file)
        to_layer = file_layer.get(to_file)
        if from_layer and to_layer and from_layer != to_layer:
            dep_counts[(from_layer, to_layer)] += 1

    dependencies = [
        {"from": fl, "to": tl, "count": cnt}
        for (fl, tl), cnt in sorted(dep_counts.items(), key=lambda x: -x[1])
    ]

    return {
        "repo": str(repo_root),
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "total_files": len(file_layer),
        "layers": layers_result,
        "dependencies": dependencies,
    }
