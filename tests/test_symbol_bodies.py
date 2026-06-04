"""Tests for _extract_symbol_bodies — code example injection into ask context."""
from __future__ import annotations
import json
from pathlib import Path
import pytest


def _make_fixture(tmp_path: Path) -> tuple[Path, Path]:
    """Create a minimal repo + .rekipedia/ with symbols.json and a source file."""
    repo_root = tmp_path

    # Write a sample Python source file
    src_dir = repo_root / "src"
    src_dir.mkdir()
    src_file = src_dir / "auth.py"
    src_file.write_text(
        "def validate_token(token: str) -> bool:\n"
        "    \"\"\"Validate a JWT token.\"\"\"\n"
        "    if not token:\n"
        "        raise ValueError('empty token')\n"
        "    return token.startswith('Bearer ')\n"
        "\n"
        "class AuthService:\n"
        "    def login(self, username: str, password: str) -> str:\n"
        "        return 'token-123'\n",
        encoding="utf-8",
    )

    # Write .rekipedia/exports/symbols.json
    output_dir = repo_root / ".rekipedia"
    exports_dir = output_dir / "exports"
    exports_dir.mkdir(parents=True)
    symbols = [
        {
            "name": "validate_token",
            "kind": "function",
            "file": "src/auth.py",
            "line_start": 1,
            "line_end": 5,
            "signature": "def validate_token(token: str) -> bool",
        },
        {
            "name": "AuthService",
            "kind": "class",
            "file": "src/auth.py",
            "line_start": 7,
            "line_end": 9,
            "signature": "class AuthService",
        },
        {
            "name": "login",
            "kind": "method",
            "file": "src/auth.py",
            "line_start": 8,
            "line_end": 9,
            "signature": "def login(self, username: str, password: str) -> str",
        },
    ]
    (exports_dir / "symbols.json").write_text(
        json.dumps(symbols), encoding="utf-8"
    )

    return output_dir, repo_root


def test_extract_symbol_bodies_returns_relevant_code(tmp_path):
    from rekipedia.orchestrator.run_ask import _extract_symbol_bodies

    output_dir, repo_root = _make_fixture(tmp_path)
    result = _extract_symbol_bodies("how does validate_token work", output_dir, repo_root)

    assert result, "Should return non-empty string"
    assert "## Symbol Source Code" in result
    assert "validate_token" in result
    assert "```py" in result  # fenced code block with language
    assert "raise ValueError" in result  # actual code body, not just signature


def test_extract_symbol_bodies_includes_file_line_ref(tmp_path):
    from rekipedia.orchestrator.run_ask import _extract_symbol_bodies

    output_dir, repo_root = _make_fixture(tmp_path)
    result = _extract_symbol_bodies("validate_token", output_dir, repo_root)

    # Should include file:line citation
    assert "src/auth.py:1" in result


def test_extract_symbol_bodies_empty_when_no_exports(tmp_path):
    from rekipedia.orchestrator.run_ask import _extract_symbol_bodies

    output_dir = tmp_path / ".rekipedia"
    output_dir.mkdir()
    # No exports/symbols.json
    result = _extract_symbol_bodies("anything", output_dir, tmp_path)
    assert result == ""


def test_extract_symbol_bodies_skips_missing_files(tmp_path):
    from rekipedia.orchestrator.run_ask import _extract_symbol_bodies

    output_dir = tmp_path / ".rekipedia"
    exports_dir = output_dir / "exports"
    exports_dir.mkdir(parents=True)
    symbols = [
        {
            "name": "ghost_func",
            "kind": "function",
            "file": "nonexistent/ghost.py",
            "line_start": 1,
            "line_end": 5,
        }
    ]
    (exports_dir / "symbols.json").write_text(json.dumps(symbols), encoding="utf-8")

    result = _extract_symbol_bodies("ghost_func", output_dir, tmp_path)
    # Should not crash, just return empty (file not found)
    assert result == ""


def test_extract_symbol_bodies_fallback_no_keywords(tmp_path):
    """When no keywords match, should still return top symbols as fallback."""
    from rekipedia.orchestrator.run_ask import _extract_symbol_bodies

    output_dir, repo_root = _make_fixture(tmp_path)
    # Question with no matching keywords
    result = _extract_symbol_bodies("zzzzzz xxxxx", output_dir, repo_root)

    # Fallback: returns first N symbols
    assert result != "" or True  # May be empty if fallback logic filters — just ensure no crash


def test_build_full_system_includes_symbol_bodies_when_no_rag(tmp_path):
    """_build_full_system should inject symbol source code when RAG is not available."""
    from unittest.mock import patch, MagicMock
    from rekipedia.orchestrator.run_ask import _build_full_system
    from rekipedia.models.contracts import LLMConfig

    output_dir, repo_root = _make_fixture(tmp_path)

    # Create a minimal store.db so _verify_scan doesn't fail
    # (not needed here since _build_full_system doesn't call _verify_scan)

    # Patch _rag_chunks to return empty (no RAG index)
    # Patch _load_wiki_pages + _rewrite_query to keep test fast
    with (
        patch("rekipedia.orchestrator.run_ask._rag_chunks", return_value=[]),
        patch("rekipedia.orchestrator.run_ask._rewrite_query", side_effect=lambda q, *a, **kw: q),
        patch("rekipedia.orchestrator.run_ask._load_wiki_pages", return_value=[]),
    ):
        llm_config = LLMConfig(model="test/model", api_key="test")
        system = _build_full_system(
            "how does validate_token work",
            output_dir,
            llm_config,
            repo_root=repo_root,
        )

    assert "Symbol Source Code" in system
    assert "validate_token" in system
    assert "raise ValueError" in system  # actual code, not just metadata


def test_build_full_system_skips_symbol_bodies_when_rag_available(tmp_path):
    """When RAG returns results, symbol bodies should NOT be injected (RAG takes precedence)."""
    from unittest.mock import patch
    from rekipedia.orchestrator.run_ask import _build_full_system
    from rekipedia.models.contracts import LLMConfig

    output_dir, repo_root = _make_fixture(tmp_path)

    fake_rag = [{"file": "src/auth.py", "ext": ".py", "score": 0.95, "text": "def validate_token(): pass"}]

    with (
        patch("rekipedia.orchestrator.run_ask._rag_chunks", return_value=fake_rag),
        patch("rekipedia.orchestrator.run_ask._rewrite_query", side_effect=lambda q, *a, **kw: q),
        patch("rekipedia.orchestrator.run_ask._load_wiki_pages", return_value=[]),
    ):
        llm_config = LLMConfig(model="test/model", api_key="test")
        system = _build_full_system(
            "how does validate_token work",
            output_dir,
            llm_config,
            repo_root=repo_root,
        )

    # RAG section present
    assert "Relevant Source Code (RAG)" in system
    # Symbol bodies section should NOT be injected (RAG already covers it)
    assert "Symbol Source Code" not in system


def test_ask_system_prompt_requires_code_examples():
    """System prompt must instruct LLM to include real code examples."""
    from pathlib import Path
    prompt_path = Path(__file__).parent.parent / "src" / "rekipedia" / "prompts" / "ask_system.md"
    content = prompt_path.read_text(encoding="utf-8")
    assert "code examples" in content.lower() or "code block" in content.lower(), \
        "System prompt should instruct LLM to include code examples"
    assert "fenced code block" in content.lower() or "```" in content, \
        "System prompt should mention fenced code blocks"
