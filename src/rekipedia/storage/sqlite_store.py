"""Persistence layer for rekipedia — thin facade over focused storage modules.

Uses Turso (pyturso) when available — MVCC engine, cross-platform pre-built
wheels for macOS and Linux x86_64.  Falls back transparently to the stdlib
``sqlite3`` module on platforms where a pyturso wheel is not yet available
(e.g. Linux aarch64, Windows).  The public API of SqliteStore is identical
in both modes.
"""
from __future__ import annotations

import functools  # noqa: F401 — used for future lru_cache if needed
from pathlib import Path
from typing import Any

from rekipedia.storage.connection import ConnectionMixin, _Conn  # noqa: F401
from rekipedia.storage.migrations import MigrationsMixin
from rekipedia.storage.writes import WritesMixin
from rekipedia.storage.reads import ReadsMixin
from rekipedia.storage.analytics import AnalyticsMixin
from rekipedia.storage._helpers import _now  # noqa: F401 — re-exported for compat


class SqliteStore(ConnectionMixin, MigrationsMixin, WritesMixin, ReadsMixin, AnalyticsMixin):
    """Wraps a database connection for the rekipedia store.

    Uses Turso (pyturso) when available; falls back to stdlib sqlite3.
    Usage::

        store = SqliteStore(Path(".rekipedia/store.db"))
        store.open()
        # … use store methods …
        store.close()

    Also usable as a context manager::

        with SqliteStore(path) as store:
            store.upsert_run(run_id, repo_path)
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._conn: _Conn | None = None
        self._known_tables: set | None = None
