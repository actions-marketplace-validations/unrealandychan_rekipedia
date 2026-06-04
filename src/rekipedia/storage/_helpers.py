"""Shared helpers for rekipedia storage modules."""
from __future__ import annotations

from datetime import UTC, datetime


def _now() -> str:
    return datetime.now(UTC).isoformat()
