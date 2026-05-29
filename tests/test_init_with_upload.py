"""Tests for reki init --with-ci --with-upload."""
from pathlib import Path

from click.testing import CliRunner

from rekipedia.cli.init import init_cmd

WORKFLOW_REL = Path(".github") / "workflows" / "rekipedia-wiki.yml"


def _invoke_and_get_workflow(tmp_path, args):
    runner = CliRunner()
    iso_path = None
    with runner.isolated_filesystem(temp_dir=tmp_path) as iso:
        iso_path = Path(iso)
        result = runner.invoke(init_cmd, args)
    return result, iso_path


def test_with_upload_s3_writes_s3_step(tmp_path):
    (tmp_path / ".git").mkdir()
    result, iso = _invoke_and_get_workflow(tmp_path, ["--with-ci", "--with-upload", "s3", "."])
    assert result.exit_code == 0
    workflow_file = iso / WORKFLOW_REL
    assert workflow_file.exists()
    content = workflow_file.read_text()
    assert "AWS_ACCESS_KEY_ID" in content
    assert "REKIPEDIA_S3_BUCKET" in content


def test_with_upload_without_with_ci_errors(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(init_cmd, ["--with-upload", "s3", "."])
    assert result.exit_code != 0 or "--with-ci" in result.output or "Error" in result.output


def test_with_upload_gcs_writes_gcs_step(tmp_path):
    (tmp_path / ".git").mkdir()
    result, iso = _invoke_and_get_workflow(tmp_path, ["--with-ci", "--with-upload", "gcs", "."])
    assert result.exit_code == 0
    workflow_file = iso / WORKFLOW_REL
    assert workflow_file.exists()
    content = workflow_file.read_text()
    assert "GCP_CREDENTIALS" in content
    assert "REKIPEDIA_GCS_BUCKET" in content


def test_existing_with_ci_unchanged_without_upload(tmp_path):
    (tmp_path / ".git").mkdir()
    result, iso = _invoke_and_get_workflow(tmp_path, ["--with-ci", "."])
    assert result.exit_code == 0
    workflow_file = iso / WORKFLOW_REL
    assert workflow_file.exists()
    content = workflow_file.read_text()
    assert "AWS_ACCESS_KEY_ID" not in content
    assert "GCP_CREDENTIALS" not in content
