"""Recursive Language Model (RLM) reasoning loop for `rekipedia ask` (Beta).

In RLM mode, the language model can interact with the codebase context by writing
and executing Python code in a local REPL environment. It can use helper functions
to query database, read source files, and launch sub-LM calls recursively.
"""
from __future__ import annotations

import io
import json
import logging
import os
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

from rekipedia.llm.client import LLMClient
from rekipedia.models.contracts import LLMConfig
from rekipedia.orchestrator.run_ask import _verify_scan, _rag_chunks
from rekipedia.storage.sqlite_store import SqliteStore

logger = logging.getLogger("rekipedia.rlm_ask")

_MAX_ITER = int(os.environ.get("REKIPEDIA_RLM_MAX_ITER", "5"))


class RLMREPLEnv:
    """Python execution environment for RLM reasoning."""

    def __init__(self, repo_root: Path, output_dir: Path, llm_config: LLMConfig) -> None:
        self.repo_root = repo_root
        self.output_dir = output_dir
        self.llm_config = llm_config
        self.client = LLMClient(llm_config)
        self.final_answer: str | None = None
        self._symbol_cache: list[dict] | None = None

        # Build execution context
        self.locals = {
            "search_code": self.search_code,
            "get_symbol": self.get_symbol,
            "get_relationships": self.get_relationships,
            "get_page": self.get_page,
            "read_source": self.read_source,
            "sub_lm": self.sub_lm,
            "finish": self.finish,
        }

    def _get_symbols(self) -> list[dict]:
        if self._symbol_cache is None:
            symbols_path = self.output_dir / "exports" / "symbols.json"
            if symbols_path.exists():
                try:
                    self._symbol_cache = json.loads(symbols_path.read_text(encoding="utf-8"))
                except Exception:
                    self._symbol_cache = []
            else:
                self._symbol_cache = []
        return self._symbol_cache or []

    def search_code(self, query: str, top_k: int = 5) -> str:
        """Search for relevant source code chunks using semantic/RAG search."""
        chunks = _rag_chunks(query, self.output_dir, self.llm_config, top_k=top_k)
        if not chunks:
            return "No matching code chunks found."
        parts = []
        for c in chunks:
            file_ = c.get("file", "")
            ext = c.get("ext", "").lstrip(".")
            score = c.get("score", 0.0)
            text = c.get("text", "")
            parts.append(f"### `{file_}` (score={score:.2f})\n```{ext}\n{text}\n```")
        return "\n\n".join(parts)

    def get_symbol(self, name: str) -> str:
        """Look up symbol details (file, signature, kind)."""
        symbols = self._get_symbols()
        matches = [s for s in symbols if s.get("name", "").lower() == name.lower()]
        if not matches:
            matches = [s for s in symbols if name.lower() in s.get("name", "").lower()][:5]
        if not matches:
            return f"Symbol '{name}' not found."
        parts = []
        for s in matches[:5]:
            line = f"Symbol: {s.get('name')} ({s.get('kind', '?')}) in `{s.get('file', '?')}`"
            if s.get("signature"):
                line += f"\nSignature:\n{s['signature']}"
            parts.append(line)
        return "\n\n".join(parts)

    def get_relationships(self, target: str) -> str:
        """Get known relationships for a target symbol or file."""
        db_path = self.output_dir / "store.db"
        if not db_path.exists():
            return "No relationship database found."
        try:
            with SqliteStore(db_path) as store:
                run_id = store.get_latest_run_id(str(self.repo_root))
                if run_id is None:
                    run_id = store.get_latest_run_id(str(self.output_dir.parent))
                if run_id is None:
                    return "No successful scan runs found in database."
                all_rels = store.get_all_relationships(run_id)
            matches = [
                r for r in all_rels
                if target.lower() in str(r.get("source", "")).lower()
                or target.lower() in str(r.get("target", "")).lower()
            ][:15]
            if not matches:
                return f"No relationships found for target '{target}'."
            return "\n".join(
                f"- {r.get('source')} --[{r.get('kind')}]--> {r.get('target')}"
                for r in matches
            )
        except Exception as e:
            return f"Error querying relationships: {e}"

    def get_page(self, slug: str) -> str:
        """Get the full content of a wiki page."""
        wiki_dir = self.output_dir / "wiki"
        path = wiki_dir / f"{slug}.md"
        if not path.exists():
            candidates = list(wiki_dir.glob("*.md")) if wiki_dir.exists() else []
            for c in candidates:
                if slug.lower() in c.stem.lower():
                    path = c
                    break
            else:
                available = ", ".join(c.stem for c in candidates[:10])
                return f"Wiki page '{slug}' not found. Available pages: {available}"
        try:
            return path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading page '{slug}': {e}"

    def read_source(self, file: str, line_start: int | None = None, line_end: int | None = None) -> str:
        """Read source lines of a file from disk."""
        path = Path(file)
        if not path.is_absolute():
            path = self.repo_root / path
        if not path.exists():
            return f"File '{file}' not found."
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            start = max(1, line_start or 1)
            end = min(len(lines), line_end or len(lines))
            selected = lines[start - 1 : end]
            return "\n".join(f"{start + i}| {line}" for i, line in enumerate(selected))
        except Exception as e:
            return f"Error reading file '{file}': {e}"

    def sub_lm(self, prompt: str) -> str:
        """Recursively query a sub-LM with a specific reasoning prompt."""
        try:
            return self.client.call(prompt, system="You are a helpful, precise engineering sub-agent.")
        except Exception as e:
            return f"Sub-LM call failed: {e}"

    def finish(self, answer: str) -> None:
        """Finalize the answer and exit the reasoning loop."""
        self.final_answer = answer

    def execute(self, code_block: str) -> str:
        """Execute a Python code block and capture output."""
        f = io.StringIO()
        with redirect_stdout(f):
            try:
                exec(code_block, {}, self.locals)
            except Exception as e:
                import traceback
                traceback.print_exc()
        return f.getvalue()


class RLMAskAgent:
    """Agent that orchestrates the RLM reasoning loop using code execution."""

    def __init__(self, repo_root: Path, output_dir: Path, llm_config: LLMConfig) -> None:
        self.repo_root = repo_root
        self.output_dir = output_dir
        self.llm_config = llm_config
        self.client = LLMClient(llm_config)
        self.env = RLMREPLEnv(repo_root, output_dir, llm_config)

    def run(self, question: str, history: list[dict] | None = None, max_iter: int = _MAX_ITER) -> str:
        # Build initial system prompt for RLM agent
        system_prompt = (
            "You are an expert software engineering agent with access to a local Python REPL environment "
            "designed to analyze this codebase. You are running in Recursive Language Model (RLM) mode.\n\n"
            "At each step, write a Python script inside a `python` code block. The system will run your code "
            "and return its print/stdout output to you. Use this to recursively query context, inspect symbols, "
            "or run sub-LM calls for reasoning. When you have gathered enough information, call `finish(answer)` "
            "with your final comprehensive answer in Markdown.\n\n"
            "### Available Helper Functions:\n"
            "- `search_code(query, top_k=5)`: Semantic/RAG search over codebase snippets.\n"
            "- `get_symbol(name)`: Look up signature and location of a class/function/method.\n"
            "- `get_relationships(target)`: Trace import/dependency connections in the codebase.\n"
            "- `get_page(slug)`: Load a wiki documentation page by name.\n"
            "- `read_source(file, line_start=None, line_end=None)`: Read specific lines from a file on disk.\n"
            "- `sub_lm(prompt)`: Ask a sub-LM to solve, summarize, or analyze a specific sub-problem.\n"
            "- `finish(answer)`: Complete the task and provide the final answer to the user.\n\n"
            "### Example:\n"
            "```python\n"
            "# 1. Search for authentication\n"
            "res = search_code('auth flow', top_k=2)\n"
            "print('Search Results:', res)\n"
            "# 2. Call sub-LM to summarize\n"
            "summary = sub_lm(f'Explain this code:\\n{res}')\n"
            "print('Summary:', summary)\n"
            "# 3. Finalize\n"
            "finish(f'Here is the auth flow summary:\\n\\n{summary}')\n"
            "```\n"
            "Begin! Write your Python code block to start investigating."
        )

        # We will build history_turns to pass to client.call
        history_turns: list[dict[str, str]] = []
        if history:
            history_turns.extend(history)

        current_prompt = f"User Question: {question}"

        for _iteration in range(max_iter):
            try:
                response = self.client.call(
                    prompt=current_prompt,
                    system=system_prompt,
                    history=history_turns,
                )
            except Exception as e:
                logger.warning("RLM ask model call failed: %s", e)
                return f"Error executing RLM loop: {e}"

            # Append the prompt and response to history_turns for next iteration
            history_turns.append({"role": "user", "content": current_prompt})
            history_turns.append({"role": "assistant", "content": response})

            if self.env.final_answer is not None:
                return self.env.final_answer

            # Find python code block
            match = re.search(r"```python\s*(.*?)\s*```", response, re.DOTALL)
            if not match:
                # If no code block, prompt the model to write code or finish
                current_prompt = (
                    "Observation: No python code block found in your response. "
                    "Please write a python code block to continue your investigation, "
                    "or call `finish(answer)` inside a python block to deliver the final answer."
                )
                continue

            code_block = match.group(1)
            observation = self.env.execute(code_block)

            if self.env.final_answer is not None:
                return self.env.final_answer

            current_prompt = f"REPL Observation/Output:\n```\n{observation}\n```"

        # Max iterations reached fallback
        if self.env.final_answer is not None:
            return self.env.final_answer

        return "Reasoning loop timed out before finalizing the answer. Please try asking again or with a more specific query."


def run_rlm_ask(
    question: str,
    repo_root: Path,
    output_dir: Path,
    llm_config: LLMConfig | None = None,
    history: list[dict] | None = None,
) -> str:
    """Answer question using Recursive Language Model (RLM) reasoning mode (Beta)."""
    llm_config = llm_config or LLMConfig()
    _verify_scan(output_dir, repo_root)
    agent = RLMAskAgent(repo_root, output_dir, llm_config)
    return agent.run(question, history=history)
