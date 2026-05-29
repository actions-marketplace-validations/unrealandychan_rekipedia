"""Tests for reki watch --publish and team.auto_watch_publish config (#185)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from rekipedia.cli.watch import watch_cmd
from rekipedia.watcher.watcher import _RepoWatcher

# ── _RepoWatcher post_update_hook ─────────────────────────────────────────────

class TestRepoWatcherPublishHook:
    def test_hook_called_after_successful_update(self):
        """post_update_hook is called after subprocess update succeeds."""
        hook = MagicMock()
        rw = _RepoWatcher("/fake/repo", debounce_seconds=0.0, post_update_hook=hook)
        with patch("subprocess.run"):
            rw._dirty = True
            rw._trigger()
        hook.assert_called_once()

    def test_hook_not_called_when_update_fails(self):
        """post_update_hook is NOT called when subprocess.run raises."""
        hook = MagicMock()
        rw = _RepoWatcher("/fake/repo", debounce_seconds=0.0, post_update_hook=hook)
        with patch("subprocess.run", side_effect=OSError("fail")):
            rw._dirty = True
            rw._trigger()
        hook.assert_not_called()

    def test_hook_exception_does_not_crash_watcher(self):
        """If the publish hook raises, _trigger should still not propagate."""
        hook = MagicMock(side_effect=RuntimeError("publish exploded"))
        rw = _RepoWatcher("/fake/repo", debounce_seconds=0.0, post_update_hook=hook)
        with patch("subprocess.run"):
            rw._dirty = True
            rw._trigger()  # must not raise


# ── CLI --publish flag ────────────────────────────────────────────────────────

class TestWatchStartPublishFlag:
    def test_publish_flag_calls_auto_publish(self, tmp_path):
        """When --publish is passed, _auto_publish is called after each update."""
        runner = CliRunner()
        cfg_path = tmp_path / "watch.json"
        config_data = {"team": {"sync_dir": str(tmp_path / "out")}}

        with (
            patch("rekipedia.watcher.watcher.CONFIG_PATH", cfg_path),
            patch("rekipedia.config.loader.load_config", return_value=config_data),
            patch("rekipedia.watcher.watcher.start_watching") as mock_sw,
        ):
            result = runner.invoke(watch_cmd, ["start", str(tmp_path), "--publish"])

        assert result.exit_code == 0
        mock_sw.assert_called_once()
        _, kwargs = mock_sw.call_args
        assert kwargs["post_update_hook"] is not None

    def test_auto_watch_publish_config_enables_publish(self, tmp_path):
        """When team.auto_watch_publish is true in config, publish runs without --publish flag."""
        runner = CliRunner()
        cfg_path = tmp_path / "watch.json"
        config_data = {
            "team": {
                "auto_watch_publish": True,
                "sync_dir": str(tmp_path / "out"),
            }
        }

        with (
            patch("rekipedia.watcher.watcher.CONFIG_PATH", cfg_path),
            patch("rekipedia.config.loader.load_config", return_value=config_data),
            patch("rekipedia.watcher.watcher.start_watching") as mock_sw,
        ):
            # No --publish flag passed
            result = runner.invoke(watch_cmd, ["start", str(tmp_path)])

        assert result.exit_code == 0
        mock_sw.assert_called_once()
        _, kwargs = mock_sw.call_args
        assert kwargs["post_update_hook"] is not None

    def test_no_publish_flag_no_hook(self, tmp_path):
        """Without --publish and auto_watch_publish=False, no hook is passed."""
        runner = CliRunner()
        cfg_path = tmp_path / "watch.json"
        config_data = {"team": {"sync_dir": str(tmp_path / "out")}}

        with (
            patch("rekipedia.watcher.watcher.CONFIG_PATH", cfg_path),
            patch("rekipedia.config.loader.load_config", return_value=config_data),
            patch("rekipedia.watcher.watcher.start_watching") as mock_sw,
        ):
            result = runner.invoke(watch_cmd, ["start", str(tmp_path)])

        assert result.exit_code == 0
        _, kwargs = mock_sw.call_args
        assert kwargs["post_update_hook"] is None

    def test_publish_warns_when_no_dir_configured(self, tmp_path):
        """--publish with no sync_dir or publish_dir prints a warning."""
        runner = CliRunner()
        cfg_path = tmp_path / "watch.json"
        config_data = {"team": {}}

        with (
            patch("rekipedia.watcher.watcher.CONFIG_PATH", cfg_path),
            patch("rekipedia.config.loader.load_config", return_value=config_data),
            patch("rekipedia.watcher.watcher.start_watching") as mock_sw,
        ):
            result = runner.invoke(watch_cmd, ["start", str(tmp_path), "--publish"])

        assert result.exit_code == 0
        assert "no publish dir" in result.output.lower() or "⚠" in result.output
        _, kwargs = mock_sw.call_args
        assert kwargs["post_update_hook"] is None

    def test_publish_hook_invokes_auto_publish(self, tmp_path):
        """The post_update_hook created by --publish actually calls _auto_publish."""
        runner = CliRunner()
        cfg_path = tmp_path / "watch.json"
        out_dir = str(tmp_path / "out")
        config_data = {"team": {"sync_dir": out_dir}}

        captured_hook = {}

        def fake_start_watching(repos=None, debounce_seconds=2.0, post_update_hook=None):
            captured_hook["hook"] = post_update_hook

        with (
            patch("rekipedia.watcher.watcher.CONFIG_PATH", cfg_path),
            patch("rekipedia.config.loader.load_config", return_value=config_data),
            patch("rekipedia.watcher.watcher.start_watching", side_effect=fake_start_watching),
        ):
            result = runner.invoke(watch_cmd, ["start", str(tmp_path), "--publish"])

        assert result.exit_code == 0
        assert captured_hook["hook"] is not None

        # Now call the hook with _auto_publish mocked at import location inside hook
        with patch("rekipedia.orchestrator.run_digest._auto_publish") as mock_ap:
            captured_hook["hook"]()
        mock_ap.assert_called_once()
