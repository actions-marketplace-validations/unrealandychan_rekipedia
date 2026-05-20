"""rekipedia — agentic repo-to-wiki knowledge store."""
__version__ = "0.17.1"

from rekipedia.api import (  # noqa: E402
    AskResult,
    Citation,
    ScanResult,
    ask,
    ask_async,
    scan,
    scan_async,
)

__all__ = [
    "__version__",
    "scan",
    "scan_async",
    "ask",
    "ask_async",
    "ScanResult",
    "AskResult",
    "Citation",
]
