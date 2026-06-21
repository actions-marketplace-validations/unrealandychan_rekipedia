"""Tests for Recursive Language Model (RLM) reasoning loop (Beta)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from rekipedia.models.contracts import LLMConfig
from rekipedia.orchestrator.rlm_ask import RLMREPLEnv, RLMAskAgent, run_rlm_ask


def _make_config() -> LLMConfig:
    return LLMConfig(model="openai/gpt-4o-mini")


def test_rlm_repl_env_search_code_no_index(tmp_path):
    """Returns matching error message when no RAG index is available."""
    env = RLMREPLEnv(tmp_path, tmp_path, _make_config())
    result = env.search_code("test query")
    assert "No matching code chunks found" in result


def test_rlm_repl_env_get_symbol_not_found(tmp_path):
    """Returns 'not found' message when symbols.json doesn't exist."""
    env = RLMREPLEnv(tmp_path, tmp_path, _make_config())
    result = env.get_symbol("MyClass")
    assert "Symbol 'MyClass' not found" in result


def test_rlm_repl_env_get_page_not_found(tmp_path):
    """Returns helpful error when wiki page is missing."""
    env = RLMREPLEnv(tmp_path, tmp_path, _make_config())
    result = env.get_page("nonexistent")
    assert "Wiki page 'nonexistent' not found" in result


def test_rlm_repl_env_get_relationships_no_db(tmp_path):
    """Returns correct message when SQLite DB is missing."""
    env = RLMREPLEnv(tmp_path, tmp_path, _make_config())
    result = env.get_relationships("MyClass")
    assert "No relationship database found" in result


def test_rlm_repl_env_read_source(tmp_path):
    """Reads lines from source file successfully."""
    src_file = tmp_path / "hello.py"
    src_file.write_text("line1\nline2\nline3\nline4\n", encoding="utf-8")
    env = RLMREPLEnv(tmp_path, tmp_path / ".rekipedia", LLMConfig())
    res = env.read_source("hello.py", 2, 3)
    assert "2| line2" in res
    assert "3| line3" in res


def test_rlm_repl_env_execute(tmp_path):
    """Executes python code block and captures stdout and variables."""
    env = RLMREPLEnv(tmp_path, tmp_path, _make_config())
    code = "print('hello from RLM')\n"
    res = env.execute(code)
    assert "hello from RLM" in res


def test_rlm_agent_run(tmp_path):
    """Exercises the full RLMAskAgent runner loop."""
    agent = RLMAskAgent(tmp_path, tmp_path, _make_config())
    
    # We mock client.call directly
    agent.client.call = MagicMock(side_effect=[
        "Let's run some code:\n```python\nprint('Logic works')\n```",
        "Done. ```python\nfinish('Final RLM Answer')\n```"
    ])

    # We mock _verify_scan in run_rlm_ask to avoid needing a valid DB for tests
    with patch("rekipedia.orchestrator.rlm_ask._verify_scan") as mock_verify:
        ans = agent.run("How does it work?")
        assert ans == "Final RLM Answer"
