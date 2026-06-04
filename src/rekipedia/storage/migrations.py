"""Schema migration runner for rekipedia storage."""
from __future__ import annotations

from pathlib import Path

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class MigrationsMixin:
    """Mixin providing schema migration logic."""

    def current_schema_version(self) -> int:
        try:
            row = self._c.execute("SELECT MAX(version) FROM schema_version").fetchone()
            return row[0] or 0
        except Exception:
            return 0

    def _apply_migrations(self) -> None:
        current = self.current_schema_version()
        sql_files = sorted(_MIGRATIONS_DIR.glob("*.sql"))
        for sql_file in sql_files:
            version = int(sql_file.stem.split("_")[0])
            if version > current:
                sql = sql_file.read_text(encoding="utf-8")
                for stmt in sql.split(";"):
                    lines = [line for line in stmt.splitlines() if not line.strip().startswith("--")]
                    stmt = "\n".join(lines).strip()
                    if stmt:
                        self._conn.execute(stmt)
                self._conn.commit()
        self._known_tables = None
