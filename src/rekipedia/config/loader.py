"""Global + local config loader with deep-merge (issue #143)."""
from __future__ import annotations

import os
from pathlib import Path

import yaml


# Default configuration — merged before global and local configs
_DEFAULT_CONFIG: dict = {
    "documents": {
        "enabled": False,          # opt-in: enable PDF/DOCX/PPTX/XLSX extraction
        "extensions": [".pdf", ".docx", ".pptx", ".xlsx"],
        "max_file_size_mb": 50,    # skip files larger than this
        "embed_chunks": True,      # include document chunks in RAG embed index
        "wiki_page_per_doc": True, # generate a wiki page summarising each document
        "thumbnails": False,
        "thumbnail_dpi": 150,
    }
}


def get_global_config_path() -> Path:
    """Return the global rekipedia config path, respecting XDG_CONFIG_HOME."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        base = Path(xdg)
    else:
        base = Path.home() / ".config"
    return base / "rekipedia" / "config.yml"


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep-merge override into base. Dicts merged recursively; scalars/lists: override wins."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def load_config(repo: Path) -> dict:
    """Load and deep-merge default + global + local config."""
    global_path = get_global_config_path()
    global_cfg: dict = {}
    if global_path.exists():
        global_cfg = yaml.safe_load(global_path.read_text()) or {}

    local_path = repo / ".rekipedia" / "config.yml"
    local_cfg: dict = {}
    if local_path.exists():
        local_cfg = yaml.safe_load(local_path.read_text()) or {}

    merged = _deep_merge(_DEFAULT_CONFIG, global_cfg)
    return _deep_merge(merged, local_cfg)
