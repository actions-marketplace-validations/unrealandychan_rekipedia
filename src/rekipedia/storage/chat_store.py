"""Lightweight chat history store — separate from the main scan store.db.

Uses its own ``chat.db`` file so that chat history does not pollute the
shared ``store.db`` (which teams often share as a read-only artefact).

Schema mirrors the ``qa_history`` / ``qa_symbol_mentions`` tables from the
main store but lives in a standalone SQLite database.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def _chat_db_path(output_dir: Path) -> Path:
    """Return the canonical path for the chat history database.

    Args:
        output_dir: The .rekipedia/ directory for the project.

    Returns:
        Path to chat.db inside output_dir.
    """
    return Path(output_dir) / "chat.db"


class ChatStore:
    """Isolated SQLite store for per-user / per-session chat history.

    Stores only Q&A pairs and (optionally) symbol mentions — never any scan
    data.  Can coexist alongside a read-only shared ``store.db``.

    Usage::

        with ChatStore(output_dir) as cs:
            qa_id = cs.save_qa(repo_path, question, answer, model)
            history = cs.get_qa_history(repo_path)
    """

    def __init__(self, output_dir: Path | str) -> None:
        self._db_path = _chat_db_path(Path(output_dir))
        self._conn: sqlite3.Connection | None = None

    # ── context-manager support ────────────────────────────────────────────

    def __enter__(self) -> "ChatStore":
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ── lifecycle ──────────────────────────────────────────────────────────

    def open(self) -> None:
        """Open (or create) the chat database."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._ensure_schema()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── schema ─────────────────────────────────────────────────────────────

    def _ensure_schema(self) -> None:
        assert self._conn is not None
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS qa_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_path   TEXT    NOT NULL,
                question    TEXT    NOT NULL,
                answer      TEXT    NOT NULL,
                model       TEXT    NOT NULL DEFAULT '',
                created_at  TEXT    NOT NULL
                            DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            );

            CREATE TABLE IF NOT EXISTS qa_symbol_mentions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                qa_id       INTEGER NOT NULL REFERENCES qa_history(id),
                symbol_name TEXT    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_qa_repo
                ON qa_history(repo_path, id DESC);

            CREATE INDEX IF NOT EXISTS idx_qa_sym_qa_id
                ON qa_symbol_mentions(qa_id);
            """
        )
        self._conn.commit()

    # ── writes ─────────────────────────────────────────────────────────────

    def save_qa(
        self,
        repo_path: str,
        question: str,
        answer: str,
        model: str = "",
    ) -> int:
        """Persist a Q&A pair to chat.db.

        Args:
            repo_path: Absolute path of the scanned repository.
            question: User question string.
            answer: LLM answer string.
            model: Model identifier (e.g. ``"gemini/gemini-1.5-pro"``).

        Returns:
            The new ``qa_history`` row id.
        """
        assert self._conn is not None
        cur = self._conn.execute(
            "INSERT INTO qa_history (repo_path, question, answer, model)"
            " VALUES (?, ?, ?, ?)",
            (repo_path, question, answer, model),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def save_qa_symbol_mentions(self, qa_id: int, symbol_names: list[str]) -> None:
        """Record which symbols were mentioned in an answer.

        Args:
            qa_id: Row id returned by :meth:`save_qa`.
            symbol_names: List of symbol names referenced in the answer.
        """
        assert self._conn is not None
        self._conn.executemany(
            "INSERT INTO qa_symbol_mentions (qa_id, symbol_name) VALUES (?, ?)",
            [(qa_id, s) for s in symbol_names],
        )
        self._conn.commit()

    def delete_qa(self, qa_id: int) -> None:
        """Delete a single Q&A entry and its symbol mentions.

        Args:
            qa_id: Row id to delete.
        """
        assert self._conn is not None
        self._conn.execute("DELETE FROM qa_symbol_mentions WHERE qa_id = ?", (qa_id,))
        self._conn.execute("DELETE FROM qa_history WHERE id = ?", (qa_id,))
        self._conn.commit()

    def clear_history(self, repo_path: str) -> int:
        """Delete all Q&A history for a repo. Returns rows deleted.

        Args:
            repo_path: Repo path to clear history for.

        Returns:
            Number of qa_history rows deleted.
        """
        assert self._conn is not None
        ids = [
            r[0]
            for r in self._conn.execute(
                "SELECT id FROM qa_history WHERE repo_path = ?", (repo_path,)
            ).fetchall()
        ]
        if ids:
            self._conn.executemany(
                "DELETE FROM qa_symbol_mentions WHERE qa_id = ?",
                [(i,) for i in ids],
            )
            self._conn.execute(
                "DELETE FROM qa_history WHERE repo_path = ?", (repo_path,)
            )
            self._conn.commit()
        return len(ids)

    # ── reads ──────────────────────────────────────────────────────────────

    def get_qa_history(
        self, repo_path: str, limit: int = 50
    ) -> list[dict]:
        """Return recent Q&A pairs for a repo, newest first.

        Args:
            repo_path: Repository path to filter by.
            limit: Maximum rows to return.

        Returns:
            List of dicts with keys: id, question, answer, model, created_at.
        """
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT id, question, answer, model, created_at"
            " FROM qa_history WHERE repo_path = ?"
            " ORDER BY id DESC LIMIT ?",
            (repo_path, limit),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "question": r["question"],
                "answer": r["answer"],
                "model": r["model"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
