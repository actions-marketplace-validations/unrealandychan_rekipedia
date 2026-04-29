"""Core module for mini Python fixture repo."""
from utils import add


class Calculator:
    """Simple calculator using shared utils."""

    def sum(self, a: int, b: int) -> int:
        return add(a, b)
