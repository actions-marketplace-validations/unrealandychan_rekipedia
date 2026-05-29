"""Tests for reki merge-driver command."""
from pathlib import Path

from click.testing import CliRunner

from rekipedia.cli.merge_driver_cmd import merge_driver_cmd


def write_page(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_identical_pages_exit_0(tmp_path):
    base = tmp_path / "base.md"
    ours = tmp_path / "ours.md"
    theirs = tmp_path / "theirs.md"
    write_page(base, "# Page\nSame")
    write_page(ours, "# Page\nSame")
    write_page(theirs, "# Page\nSame")
    runner = CliRunner()
    result = runner.invoke(merge_driver_cmd, [str(base), str(ours), str(theirs)])
    assert result.exit_code == 0


def test_only_theirs_changed_takes_theirs(tmp_path):
    base = tmp_path / "base.md"
    ours = tmp_path / "ours.md"
    theirs = tmp_path / "theirs.md"
    write_page(base, "# Page\nOriginal")
    write_page(ours, "# Page\nOriginal")
    write_page(theirs, "# Page\nUpdated by theirs")
    runner = CliRunner()
    result = runner.invoke(merge_driver_cmd, [str(base), str(ours), str(theirs)])
    assert result.exit_code == 0
    assert "Updated by theirs" in ours.read_text()


def test_only_ours_changed_keeps_ours(tmp_path):
    base = tmp_path / "base.md"
    ours = tmp_path / "ours.md"
    theirs = tmp_path / "theirs.md"
    write_page(base, "# Page\nOriginal")
    write_page(ours, "# Page\nUpdated by ours")
    write_page(theirs, "# Page\nOriginal")
    runner = CliRunner()
    result = runner.invoke(merge_driver_cmd, [str(base), str(ours), str(theirs)])
    assert result.exit_code == 0
    assert "Updated by ours" in ours.read_text()


def test_both_changed_exits_1_with_conflict_marker(tmp_path):
    from rekipedia.team_sync.merger import CONFLICT_MARKER

    base = tmp_path / "base.md"
    ours = tmp_path / "ours.md"
    theirs = tmp_path / "theirs.md"
    write_page(base, "# Page\nOriginal")
    write_page(ours, "# Page\nOurs changed")
    write_page(theirs, "# Page\nTheirs changed")
    runner = CliRunner()
    result = runner.invoke(merge_driver_cmd, [str(base), str(ours), str(theirs)])
    assert result.exit_code == 1
    content = ours.read_text()
    assert CONFLICT_MARKER in content
