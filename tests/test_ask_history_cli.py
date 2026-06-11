"""Tests for REPL readline history in `reki ask`."""
from __future__ import annotations

import builtins
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from click.testing import CliRunner

from rekipedia.cli.ask import (
    _add_input_history,
    _load_ask_history,
    _save_ask_history,
    ask_cmd,
)

MINI_PY = Path(__file__).parent / "fixtures" / "mini-py-repo"


# ── Helpers ─────────────────────────────────────────────────────────────────

class FakeReadline:
    """Drop-in readline substitute for testing."""

    def __init__(self) -> None:
        self._history: list[str] = []

    def read_history_file(self, path: str) -> None:
        pass

    def write_history_file(self, path: str) -> None:
        pass

    def set_history_length(self, n: int) -> None:
        pass

    def add_history(self, line: str) -> None:
        self._history.append(line)

    def get_current_history_length(self) -> int:
        return len(self._history)

    def get_history_item(self, index: int) -> str | None:
        if 1 <= index <= len(self._history):
            return self._history[index - 1]
        return None


@pytest.fixture()
def fake_rl(monkeypatch):
    """Inject a FakeReadline instance in place of the real readline module."""
    fake = FakeReadline()
    monkeypatch.setattr("rekipedia.cli.ask.readline", fake)
    return fake


@pytest.fixture()
def mini_repo(tmp_path):
    """Provide a minimal repo with a scanned store so ask_cmd can boot."""
    repo = tmp_path / "repo"
    shutil.copytree(MINI_PY, repo)
    output_dir = tmp_path / ".rekipedia"
    # Run a minimal scan so store.db exists
    from rekipedia.orchestrator.run_digest import run_digest
    from rekipedia.models.contracts import LLMConfig

    with patch("rekipedia.synthesis.page_builder.LLMClient") as MockClient:
        mock = MagicMock()
        mock.call.return_value = (
            '{"title":"T","summary":"S","key_concepts":[],'
            '"symbols":[],"relationships":[],"risks":[],'
            '"build_commands":[],"test_commands":[],"mermaid_graph":""}'
        )
        MockClient.return_value = mock
        run_digest(repo_root=repo, output_dir=output_dir, llm_config=LLMConfig(), force_local=True)
    return repo, output_dir


# ── Unit tests for history helpers ──────────────────────────────────────────

def test_add_input_history_appends_line(fake_rl):
    """_add_input_history should add a non-empty line."""
    _add_input_history("hello world")
    assert fake_rl.get_current_history_length() == 1
    assert fake_rl.get_history_item(1) == "hello world"


def test_add_input_history_skips_duplicate(fake_rl):
    """Duplicate of the most recent item should be ignored."""
    _add_input_history("first")
    _add_input_history("first")
    assert fake_rl.get_current_history_length() == 1


def test_add_input_history_allows_non_consecutive_duplicate(fake_rl):
    """Repeating an older item is allowed as long as it's not the last one."""
    _add_input_history("a")
    _add_input_history("b")
    _add_input_history("a")
    assert fake_rl.get_current_history_length() == 3


def test_add_input_history_skips_empty_string(fake_rl):
    """Empty strings should not be added."""
    _add_input_history("")
    assert fake_rl.get_current_history_length() == 0


# ── Persistence tests ───────────────────────────────────────────────────────

def test_save_ask_history_writes_file(tmp_path, monkeypatch):
    """_save_ask_history creates the history file and calls write_history_file."""
    hist_file = tmp_path / "ask_history"
    monkeypatch.setattr("rekipedia.cli.ask._HISTORY_FILE", hist_file)

    calls: list[str] = []

    class StubReadline:
        def write_history_file(self, path: str) -> None:
            calls.append(path)

    monkeypatch.setattr("rekipedia.cli.ask.readline", StubReadline())
    _save_ask_history()
    assert len(calls) == 1
    assert calls[0] == str(hist_file)


def test_load_ask_history_reads_existing_file(tmp_path, monkeypatch):
    """_load_ask_history should invoke read_history_file when file exists."""
    hist_file = tmp_path / "ask_history"
    hist_file.write_text("", encoding="utf-8")
    monkeypatch.setattr("rekipedia.cli.ask._HISTORY_FILE", hist_file)

    calls: list[str] = []

    class StubReadline:
        def read_history_file(self, path: str) -> None:
            calls.append(path)

        def set_history_length(self, n: int) -> None:
            pass

    monkeypatch.setattr("rekipedia.cli.ask.readline", StubReadline())
    _load_ask_history()
    assert len(calls) == 1
    assert calls[0] == str(hist_file)


def test_load_ask_history_ignores_missing_file(monkeypatch):
    """FileNotFoundError should be swallowed silently."""
    monkeypatch.setattr(
        "rekipedia.cli.ask._HISTORY_FILE", Path("/nonexistent/ask_history")
    )

    class StubReadline:
        def read_history_file(self, path: str) -> None:
            raise FileNotFoundError(path)

        def set_history_length(self, n: int) -> None:
            pass

    monkeypatch.setattr("rekipedia.cli.ask.readline", StubReadline())
    # Should not raise
    _load_ask_history()


# ── CLI integration tests ───────────────────────────────────────────────────

def test_ask_repl_loads_and_saves_history(mini_repo):
    """Interactive REPL should load history at startup and save on exit."""
    repo, output_dir = mini_repo
    runner = CliRunner()

    with (
        patch("rekipedia.cli.ask._load_ask_history") as mock_load,
        patch("rekipedia.cli.ask._save_ask_history") as mock_save,
        patch("rekipedia.cli.ask._answer_streaming") as mock_answer,
        patch.object(builtins, "input", side_effect=["question one", "exit"]),
    ):
        mock_answer.return_value = "answer"
        result = runner.invoke(
            ask_cmd, ["--repo", str(repo), "--output-dir", str(output_dir)]
        )

    assert result.exit_code == 0
    mock_load.assert_called_once()
    mock_save.assert_called_once()


def test_ask_repl_no_history_flag(mini_repo):
    """--no-history must prevent both load and save."""
    repo, output_dir = mini_repo
    runner = CliRunner()

    with (
        patch("rekipedia.cli.ask._load_ask_history") as mock_load,
        patch("rekipedia.cli.ask._save_ask_history") as mock_save,
        patch("rekipedia.cli.ask._answer_streaming") as mock_answer,
        patch.object(builtins, "input", side_effect=["q1", "exit"]),
    ):
        mock_answer.return_value = "ok"
        result = runner.invoke(
            ask_cmd,
            ["--repo", str(repo), "--output-dir", str(output_dir), "--no-history"],
        )

    assert result.exit_code == 0
    mock_load.assert_not_called()
    mock_save.assert_not_called()


def test_ask_repl_adds_question_to_history(mini_repo):
    """Each valid question should be pushed into readline history."""
    repo, output_dir = mini_repo
    runner = CliRunner()

    added: list[str] = []

    with (
        patch("rekipedia.cli.ask._load_ask_history"),
        patch("rekipedia.cli.ask._save_ask_history"),
        patch(
            "rekipedia.cli.ask._add_input_history", side_effect=lambda x: added.append(x)
        ),
        patch("rekipedia.cli.ask._answer_streaming") as mock_answer,
        patch.object(builtins, "input", side_effect=["How does auth work?", "exit"]),
    ):
        mock_answer.return_value = "It uses JWT."
        result = runner.invoke(
            ask_cmd, ["--repo", str(repo), "--output-dir", str(output_dir)]
        )

    assert result.exit_code == 0
    assert "How does auth work?" in added
    assert "exit" not in added  # commands like exit should not pollute history
