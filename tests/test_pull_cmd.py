"""Tests for reki pull command."""
import json
import zipfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from rekipedia.cli.pull_cmd import pull_cmd


def make_bundle_zip(tmp_path: Path, pages: dict) -> Path:
    """Create a bundle zip with the given pages."""
    import hashlib

    bundle = tmp_path / "bundle_src"
    (bundle / "pages").mkdir(parents=True)
    (bundle / "diagrams").mkdir(parents=True)
    pages_meta = []
    for slug, content in pages.items():
        h = hashlib.sha256(content.encode()).hexdigest()[:16]
        (bundle / "pages" / (slug + ".md")).write_text(content)
        pages_meta.append({"slug": slug, "content_hash": h})
    manifest = {
        "bundle_id": "abc123",
        "commit_sha": "",
        "scanned_at": "2026-01-01T00:00:00+00:00",
        "pages": pages_meta,
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    zip_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for f in bundle.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(bundle))
    return zip_path


def test_pull_dry_run_shows_manifest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    zip_path = make_bundle_zip(tmp_path, {"overview": "# Overview"})

    def fake_download(url, dest_dir):
        import shutil

        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(zip_path, dest_dir / "wiki-bundle.zip")
        return dest_dir / "wiki-bundle.zip"

    with patch("rekipedia.cli.pull_cmd.download_bundle", side_effect=fake_download):
        runner = CliRunner()
        result = runner.invoke(pull_cmd, ["https://example.com/bundle.zip", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "Dry run" in result.output


def test_pull_missing_url_reads_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("rekipedia.cli.pull_cmd.load_config", return_value={"team": {"remote_url": ""}}):
        runner = CliRunner()
        result = runner.invoke(pull_cmd, [])
    assert result.exit_code != 0
    assert "remote_url" in result.output or "URL" in result.output
