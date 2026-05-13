"""Repository file-system snapshotter.

Walks a repo root, respects ignore patterns, and returns a list of
FileManifest objects with SHA-256 hashes.
"""
from __future__ import annotations

import hashlib
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

logger = logging.getLogger("rekipedia.snapshotter")

import pathspec

from rekipedia.models.contracts import FileManifest

_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".rb": "ruby",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".dockerfile": "docker",
    ".tf": "terraform",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
}

_DEFAULT_IGNORE = [
    ".git",
    ".rekipedia",
    "__pycache__",
    "*.pyc",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    ".env",
    "*.egg-info",
    ".DS_Store",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()





def _detect_language(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if path.name.lower() == "dockerfile":
        return "docker"
    return _LANGUAGE_MAP.get(suffix)

class Snapshotter:
    """Walk *repo_root* and produce a list of :class:`FileManifest` objects."""

    def __init__(
        self,
        repo_root: Path,
        extra_ignore: list[str] | None = None,
        languages: list[str] | None = None,
    ) -> None:
        self._root = repo_root.resolve()
        patterns = list(_DEFAULT_IGNORE) + (extra_ignore or [])
        # Also honour the repo's own .gitignore if present
        gitignore = self._root / ".gitignore"
        if gitignore.exists():
            patterns += gitignore.read_text(errors="replace").splitlines()
        self._spec = pathspec.PathSpec.from_lines("gitignore", patterns)
        # Normalise to lowercase set; None means "all languages"
        self._languages: set[str] | None = (
            {lang.lower() for lang in languages} if languages else None
        )

    def _sha256(self, path: Path) -> str:
        return _sha256(path)

    def snapshot(self) -> list[FileManifest]:
        candidate_paths: list[tuple[Path, str, str | None]] = []
        for file_path in self._root.rglob("*"):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(self._root)
            if self._spec.match_file(str(rel)):
                continue
            lang = _detect_language(file_path)
            if self._languages is not None and lang not in self._languages:
                continue
            candidate_paths.append((file_path, str(rel), lang))

        manifests: list[FileManifest] = []
        with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 4)) as executor:
            future_to_meta = {
                executor.submit(self._sha256, fp): (fp, rel, lang)
                for fp, rel, lang in candidate_paths
            }
            for future in as_completed(future_to_meta):
                fp, rel, lang = future_to_meta[future]
                try:
                    sha = future.result()
                    manifests.append(
                        FileManifest(
                            path=rel,
                            sha256=sha,
                            size_bytes=fp.stat().st_size,
                            language=lang,
                        )
                    )
                except Exception as exc:
                    logger.warning("Skipping %s — could not hash: %s", fp, exc)

        return sorted(manifests, key=lambda m: m.path)
