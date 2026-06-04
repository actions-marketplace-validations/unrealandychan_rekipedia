from pathlib import Path


def _setup_wiki(wiki_dir: Path, pages: dict):
    wiki_dir.mkdir(parents=True, exist_ok=True)
    for name, content in pages.items():
        (wiki_dir / name).write_text(content)


def test_bundle_id_is_stable(tmp_path):
    """Same content → same bundle_id across two export runs."""
    from rekipedia.exporters.bundle_export import BundleExporter

    wiki1 = tmp_path / "wiki1"
    wiki2 = tmp_path / "wiki2"
    pages = {"overview.md": "# Overview\nHello world", "auth.md": "# Auth\nLogin flow"}
    _setup_wiki(wiki1, pages)
    _setup_wiki(wiki2, pages)

    diags = tmp_path / "diags"
    diags.mkdir()

    e1 = BundleExporter(wiki1, diags, tmp_path)
    m1 = e1.export(tmp_path / "bundle1")
    e2 = BundleExporter(wiki2, diags, tmp_path)
    m2 = e2.export(tmp_path / "bundle2")

    assert m1["bundle_id"] == m2["bundle_id"]


def test_hash_trailer_present(tmp_path):
    from rekipedia.exporters.bundle_export import HASH_TRAILER_PREFIX, BundleExporter

    wiki = tmp_path / "wiki"
    _setup_wiki(wiki, {"overview.md": "# Overview\nHello"})
    diags = tmp_path / "diags"
    diags.mkdir()

    e = BundleExporter(wiki, diags, tmp_path)
    e.export(tmp_path / "bundle")

    page = (tmp_path / "bundle" / "pages" / "overview.md").read_text()
    assert HASH_TRAILER_PREFIX in page


def test_manifest_has_commit_sha_key(tmp_path):
    from rekipedia.exporters.bundle_export import BundleExporter

    wiki = tmp_path / "wiki"
    _setup_wiki(wiki, {"overview.md": "# Overview"})
    diags = tmp_path / "diags"
    diags.mkdir()

    e = BundleExporter(wiki, diags, tmp_path)
    manifest = e.export(tmp_path / "bundle")

    assert "commit_sha" in manifest
    assert "bundle_id" in manifest
    assert "pages" in manifest
