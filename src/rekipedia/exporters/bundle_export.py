"""Bundle exporter — deterministic, content-addressed wiki snapshot for team sync."""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

HASH_TRAILER_PREFIX = "<!-- reki:hash:"


def _content_hash(text: str) -> str:
    # Strip any existing hash trailer before hashing (avoid circularity)
    lines = text.splitlines()
    stripped = "\n".join(line for line in lines if not line.startswith(HASH_TRAILER_PREFIX))
    return hashlib.sha256(stripped.encode()).hexdigest()[:16]


def _commit_sha(repo_root: Path) -> str:
    import subprocess

    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


class BundleExporter:
    def __init__(self, wiki_dir: Path, diagrams_dir: Path, repo_root: Path):
        self.wiki_dir = Path(wiki_dir)
        self.diagrams_dir = Path(diagrams_dir)
        self.repo_root = Path(repo_root)

    def export(self, output_dir: Path) -> dict:
        """Export wiki bundle. Returns manifest dict."""
        output_dir = Path(output_dir)
        out_pages_dir = output_dir / "pages"
        out_diagrams_dir = output_dir / "diagrams"
        out_pages_dir.mkdir(parents=True, exist_ok=True)
        out_diagrams_dir.mkdir(parents=True, exist_ok=True)

        pages_meta = []

        # Copy wiki pages with hash trailers
        if self.wiki_dir.exists():
            for md_file in sorted(self.wiki_dir.glob("*.md")):
                slug = md_file.stem
                content = md_file.read_text(encoding="utf-8")
                h = _content_hash(content)
                content_with_hash = content.rstrip() + f"\n{HASH_TRAILER_PREFIX}{h} -->\n"
                dest = out_pages_dir / md_file.name
                dest.write_text(content_with_hash, encoding="utf-8")
                pages_meta.append({"slug": slug, "content_hash": h})

        # Copy diagrams with hash trailers
        if self.diagrams_dir.exists():
            for md_file in sorted(self.diagrams_dir.glob("*.md")):
                slug = md_file.stem
                content = md_file.read_text(encoding="utf-8")
                h = _content_hash(content)
                content_with_hash = content.rstrip() + f"\n{HASH_TRAILER_PREFIX}{h} -->\n"
                dest = out_diagrams_dir / md_file.name
                dest.write_text(content_with_hash, encoding="utf-8")
                pages_meta.append({"slug": f"diagrams/{slug}", "content_hash": h})

        # Compute deterministic bundle_id
        sorted_map = {
            p["slug"]: p["content_hash"]
            for p in sorted(pages_meta, key=lambda x: x["slug"])
        }
        bundle_id = hashlib.sha256(
            json.dumps(sorted_map, sort_keys=True).encode()
        ).hexdigest()[:16]

        manifest = {
            "bundle_id": bundle_id,
            "repo": str(self.repo_root),
            "commit_sha": _commit_sha(self.repo_root),
            "scanned_at": datetime.now(UTC).isoformat(),
            "pages": pages_meta,
        }
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        return manifest
