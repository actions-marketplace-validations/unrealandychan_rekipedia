"""Tests for reki git-history command and parser."""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from rekipedia.storage.sqlite_store import SqliteStore
from rekipedia.cli.git_history import git_history_cmd
from rekipedia.analysis.git_history import extract_git_history, save_git_history, get_file_commit_counts


def test_git_history_extraction_and_saving(tmp_path):
    # Setup mock git output
    mock_log_output = "fake_hash_1|Author One|author1@test.com|2026-06-21T05:00:00Z|feat: initial commit\nfake_hash_2|Author Two|author2@test.com|2026-06-21T06:00:00Z|feat: second commit"
    mock_show_output_1 = "10\t5\tmath_helper.py\n2\t1\tutils.py"
    mock_show_output_2 = "3\t0\tmath_helper.py"

    def mock_subprocess_run(cmd, *args, **kwargs):
        mock_res = MagicMock()
        mock_res.return_code = 0
        if "log" in cmd:
            mock_res.stdout = mock_log_output
        elif "show" in cmd:
            if "fake_hash_1" in cmd:
                mock_res.stdout = mock_show_output_1
            else:
                mock_res.stdout = mock_show_output_2
        return mock_res

    # Create mock repo directory with .git
    repo = tmp_path / "mock_repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    with patch("subprocess.run", side_effect=mock_subprocess_run):
        commits = extract_git_history(repo, "run1", limit=10)
        assert len(commits) == 2
        assert commits[0]["commit_hash"] == "fake_hash_1"
        assert len(commits[0]["file_changes"]) == 2
        assert commits[0]["file_changes"][0]["file_path"] == "math_helper.py"
        assert commits[0]["file_changes"][0]["additions"] == 10

        # Save to DB
        db_path = repo / ".rekipedia" / "store.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with SqliteStore(db_path) as store:
            store.upsert_run("run1", str(repo))
            save_git_history(store, "run1", commits)
            
            # Retrieve commit counts
            counts = get_file_commit_counts(store, "run1")
            assert counts["math_helper.py"] == 2
            assert counts["utils.py"] == 1
