"""Three-way wiki page merger for team-sync conflict-free collaboration."""
import json
from dataclasses import dataclass, field
from pathlib import Path

CONFLICT_MARKER = "<!-- reki:conflict -->"


@dataclass
class MergeReport:
    merged_clean: list = field(default_factory=list)
    merged_conflict: list = field(default_factory=list)
    added: list = field(default_factory=list)
    deleted: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "merged_clean": self.merged_clean,
            "merged_conflict": self.merged_conflict,
            "added": self.added,
            "deleted": self.deleted,
            "summary": {
                "clean": len(self.merged_clean),
                "conflict": len(self.merged_conflict),
                "added": len(self.added),
                "deleted": len(self.deleted),
            },
        }


def _load_manifest(bundle_dir: Path) -> dict:
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest.json found in {bundle_dir}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _load_pages(bundle_dir: Path, manifest: dict) -> dict[str, str]:
    """Returns {slug: content} for all pages in the bundle."""
    pages = {}
    for page in manifest["pages"]:
        slug = page["slug"]
        if slug.startswith("diagrams/"):
            f = bundle_dir / "diagrams" / (slug[len("diagrams/"):] + ".md")
        else:
            f = bundle_dir / "pages" / (slug + ".md")
        if f.exists():
            pages[slug] = f.read_text(encoding="utf-8")
    return pages


def _get_hash(manifest: dict, slug: str) -> str | None:
    for p in manifest["pages"]:
        if p["slug"] == slug:
            return p["content_hash"]
    return None


class WikiMerger:
    def __init__(self, bundle_a: Path, bundle_b: Path, base: Path | None = None):
        self.bundle_a = Path(bundle_a)
        self.bundle_b = Path(bundle_b)
        self.base = Path(base) if base else None

    def merge(self, output_dir: Path) -> MergeReport:
        output_dir = Path(output_dir)
        (output_dir / "pages").mkdir(parents=True, exist_ok=True)
        (output_dir / "diagrams").mkdir(parents=True, exist_ok=True)

        manifest_a = _load_manifest(self.bundle_a)
        manifest_b = _load_manifest(self.bundle_b)
        manifest_base = _load_manifest(self.base) if self.base else None

        pages_a = _load_pages(self.bundle_a, manifest_a)
        pages_b = _load_pages(self.bundle_b, manifest_b)
        pages_base = _load_pages(self.base, manifest_base) if manifest_base else {}

        all_slugs = set(pages_a) | set(pages_b) | set(pages_base)
        report = MergeReport()

        for slug in sorted(all_slugs):
            in_a = slug in pages_a
            in_b = slug in pages_b
            in_base = slug in pages_base

            hash_a = _get_hash(manifest_a, slug) if in_a else None
            hash_b = _get_hash(manifest_b, slug) if in_b else None
            hash_base = _get_hash(manifest_base, slug) if (manifest_base and in_base) else None

            if not in_a and not in_b:
                # deleted in both → skip
                report.deleted.append(slug)
                continue

            if not in_a and in_b:
                # deleted in A, present in B (or new in B)
                if in_base and hash_b == hash_base:
                    # B unchanged from base → A deleted it → honour deletion
                    report.deleted.append(slug)
                else:
                    # B changed or no base → keep B
                    _write_page(output_dir, slug, pages_b[slug])
                    report.added.append(slug)
                continue

            if in_a and not in_b:
                # deleted in B, present in A
                if in_base and hash_a == hash_base:
                    # A unchanged from base → B deleted it → honour deletion
                    report.deleted.append(slug)
                else:
                    # A changed or no base → keep A
                    _write_page(output_dir, slug, pages_a[slug])
                    report.added.append(slug)
                continue

            # present in both
            if hash_a == hash_b:
                # identical content → keep either
                _write_page(output_dir, slug, pages_a[slug])
                report.merged_clean.append(slug)
            elif manifest_base and hash_a == hash_base:
                # only B changed
                _write_page(output_dir, slug, pages_b[slug])
                report.merged_clean.append(slug)
            elif manifest_base and hash_b == hash_base:
                # only A changed
                _write_page(output_dir, slug, pages_a[slug])
                report.merged_clean.append(slug)
            else:
                # both changed differently → conflict
                conflict_content = (
                    f"{CONFLICT_MARKER}\n"
                    f"<!-- reki:conflict:slug:{slug} -->\n\n"
                    f"### Version A (bundle_id: {manifest_a['bundle_id']})\n\n"
                    f"{pages_a[slug]}\n\n"
                    f"### Version B (bundle_id: {manifest_b['bundle_id']})\n\n"
                    f"{pages_b[slug]}\n"
                )
                _write_page(output_dir, slug, conflict_content)
                report.merged_conflict.append(slug)

        return report


def _write_page(output_dir: Path, slug: str, content: str) -> None:
    if slug.startswith("diagrams/"):
        dest = output_dir / "diagrams" / (slug[len("diagrams/"):] + ".md")
    else:
        dest = output_dir / "pages" / (slug + ".md")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
