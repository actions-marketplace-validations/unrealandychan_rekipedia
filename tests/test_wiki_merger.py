"""Tests for WikiMerger three-way merge logic."""
import json
from pathlib import Path

from rekipedia.team_sync.merger import CONFLICT_MARKER, WikiMerger


def make_bundle(tmp_path: Path, name: str, pages: dict[str, str]) -> Path:
    """Helper: create a minimal bundle dir with manifest.json and page files."""
    import hashlib

    bundle = tmp_path / name
    (bundle / "pages").mkdir(parents=True)
    (bundle / "diagrams").mkdir(parents=True)
    pages_meta = []
    for slug, content in pages.items():
        h = hashlib.sha256(content.encode()).hexdigest()[:16]
        if slug.startswith("diagrams/"):
            dest = bundle / "diagrams" / (slug[len("diagrams/"):] + ".md")
        else:
            dest = bundle / "pages" / (slug + ".md")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content + f"\n<!-- reki:hash:{h} -->\n", encoding="utf-8")
        pages_meta.append({"slug": slug, "content_hash": h})
    slug_hash_map = {p["slug"]: p["content_hash"] for p in sorted(pages_meta, key=lambda x: x["slug"])}
    bundle_id = hashlib.sha256(json.dumps(slug_hash_map, sort_keys=True).encode()).hexdigest()[:16]
    manifest = {
        "bundle_id": bundle_id,
        "repo": str(tmp_path),
        "commit_sha": "",
        "scanned_at": "2026-01-01T00:00:00+00:00",
        "pages": pages_meta,
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return bundle


def test_unchanged_pages_no_conflict(tmp_path):
    pages = {"overview": "# Overview\nSame content"}
    base = make_bundle(tmp_path, "base", pages)
    a = make_bundle(tmp_path, "a", pages)
    b = make_bundle(tmp_path, "b", pages)
    merger = WikiMerger(a, b, base=base)
    report = merger.merge(tmp_path / "out")
    assert report.merged_conflict == []
    assert "overview" in report.merged_clean


def test_only_a_changed_accepted(tmp_path):
    base = make_bundle(tmp_path, "base", {"auth": "# Auth\nOld"})
    a = make_bundle(tmp_path, "a", {"auth": "# Auth\nUpdated by A"})
    b = make_bundle(tmp_path, "b", {"auth": "# Auth\nOld"})
    merger = WikiMerger(a, b, base=base)
    report = merger.merge(tmp_path / "out")
    assert report.merged_conflict == []
    result = (tmp_path / "out" / "pages" / "auth.md").read_text()
    assert "Updated by A" in result


def test_only_b_changed_accepted(tmp_path):
    base = make_bundle(tmp_path, "base", {"auth": "# Auth\nOld"})
    a = make_bundle(tmp_path, "a", {"auth": "# Auth\nOld"})
    b = make_bundle(tmp_path, "b", {"auth": "# Auth\nUpdated by B"})
    merger = WikiMerger(a, b, base=base)
    report = merger.merge(tmp_path / "out")
    assert report.merged_conflict == []
    result = (tmp_path / "out" / "pages" / "auth.md").read_text()
    assert "Updated by B" in result


def test_both_changed_different_is_conflict(tmp_path):
    base = make_bundle(tmp_path, "base", {"auth": "# Auth\nOriginal"})
    a = make_bundle(tmp_path, "a", {"auth": "# Auth\nA version"})
    b = make_bundle(tmp_path, "b", {"auth": "# Auth\nB version"})
    merger = WikiMerger(a, b, base=base)
    report = merger.merge(tmp_path / "out")
    assert "auth" in report.merged_conflict
    result = (tmp_path / "out" / "pages" / "auth.md").read_text()
    assert CONFLICT_MARKER in result


def test_new_page_in_a_added(tmp_path):
    base = make_bundle(tmp_path, "base", {})
    a = make_bundle(tmp_path, "a", {"new-page": "# New\nContent"})
    b = make_bundle(tmp_path, "b", {})
    merger = WikiMerger(a, b, base=base)
    report = merger.merge(tmp_path / "out")
    assert "new-page" in report.added
    assert (tmp_path / "out" / "pages" / "new-page.md").exists()
