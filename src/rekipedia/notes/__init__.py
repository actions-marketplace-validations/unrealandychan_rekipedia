"""Import notes from YAML or Markdown files."""
from __future__ import annotations

from pathlib import Path


def import_notes_from_file(path: Path) -> list[dict]:
    """Parse a YAML or Markdown file and return list of note dicts."""
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        return _import_yaml(path)
    elif suffix in (".md", ".markdown"):
        return _import_markdown(path)
    else:
        # Try YAML first, then markdown
        try:
            return _import_yaml(path)
        except Exception:
            return _import_markdown(path)


def _import_yaml(path: Path) -> list[dict]:
    import yaml  # type: ignore[import]
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    notes = []
    for item in data:
        if not isinstance(item, dict):
            continue
        content = item.get("content", "").strip()
        if not content:
            continue
        tags_raw = item.get("tags", [])
        if isinstance(tags_raw, list):
            tags = ",".join(str(t) for t in tags_raw)
        else:
            tags = str(tags_raw)
        notes.append({"content": content, "tags": tags})
    return notes


def _import_markdown(path: Path) -> list[dict]:
    """Parse markdown: each ## Section becomes a note."""
    text = path.read_text(encoding="utf-8")
    notes = []
    current_title: str | None = None
    current_lines: list[str] = []
    current_tags = ""

    def _flush() -> None:
        nonlocal current_tags
        if current_title is None:
            return
        body_lines = []
        tags = ""
        # Check for tags: line at top of body
        stripped = [l for l in current_lines if l.strip()]
        if stripped and stripped[0].lower().startswith("tags:"):
            tags = stripped[0].split(":", 1)[1].strip()
            body_lines = current_lines[current_lines.index(stripped[0]) + 1:]
        else:
            body_lines = current_lines
            tags = current_tags

        content = (current_title + "\n" + "\n".join(body_lines)).strip()
        if content:
            notes.append({"content": content, "tags": tags})
        current_tags = ""

    for line in text.splitlines():
        if line.startswith("## "):
            _flush()
            current_title = line[3:].strip()
            current_lines = []
        elif current_title is not None:
            current_lines.append(line)

    _flush()
    return notes
