"""Shared slug normalisation utilities for the synthesis pipeline."""
from __future__ import annotations

import re


def sanitize_slug(slug: str) -> str:
    """Normalise a slug: lowercase, replace bad chars with hyphens, collapse runs."""
    slug = slug.lower().strip()
    slug = re.sub(r"[^a-z0-9_-]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "untitled"


# Keep private alias for backwards compatibility within the package
_sanitize_slug = sanitize_slug
