"""DB connection helpers for rekipedia storage."""
from __future__ import annotations

from typing import Any

try:
    import turso as _db

    def _connect(path: str) -> Any:
        conn = _db.connect(path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-64000")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn

    _BACKEND = "turso"
except ImportError:  # pragma: no cover
    import sqlite3 as _db_sqlite3  # type: ignore[assignment]

    def _connect(path: str) -> Any:  # type: ignore[misc]
        conn = _db_sqlite3.connect(path, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-64000")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn

    _BACKEND = "sqlite3"

# Type alias
_Conn = Any


class ConnectionMixin:
    """Mixin providing DB open/close/context-manager lifecycle."""

    def open(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = _connect(str(self._path))
        self._apply_migrations()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @property
    def _c(self) -> _Conn:
        if self._conn is None:
            raise RuntimeError("SqliteStore is not open. Call open() first.")
        return self._conn

    @property
    def db(self) -> _Conn:
        """Raw connection. Prefer the typed helper methods over direct access."""
        return self._c

    def table_names(self) -> set[str]:
        """Return names of all user tables in the database."""
        return self._table_names()

    def _table_names(self) -> set[str]:
        if self._known_tables is not None:
            return self._known_tables
        rows = self._c.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        self._known_tables = {r[0] for r in rows}
        return self._known_tables
