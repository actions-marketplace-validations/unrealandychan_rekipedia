"""OSC-8 terminal hyperlink utilities.

OSC 8 standard: https://gist.github.com/egmontkob/eb114294efbcd5adb1944c9f3cb5feda

Format:  ESC ] 8 ; params ; URI ST  text  ESC ] 8 ; ; ST
where ST (String Terminator) is ESC \\ (two chars: 0x1b 0x5c).

Auto-detection
--------------
OSC-8 is supported by: iTerm2, WezTerm, Kitty, Foot, GNOME Terminal ≥3.26,
Alacritty, Windows Terminal, VSCode integrated terminal, tmux ≥3.3a.

We enable OSC-8 when ANY of the following are true:
- TERM_PROGRAM in {iTerm.app, WezTerm, vscode}
- COLORTERM == truecolor or 24bit
- TERM starts with xterm or contains 256color
- REKIPEDIA_OSC8=1 is set explicitly

Disable by setting REKIPEDIA_OSC8=0.
"""
from __future__ import annotations

import os
import sys

__all__ = [
    "file_hyperlink",
    "hyperlink",
    "osc8_supported",
    "print_citations",
]

_FORCE_ENV = os.environ.get("REKIPEDIA_OSC8", "")


def osc8_supported() -> bool:
    """Return True if the current terminal is likely to render OSC-8 hyperlinks."""
    if _FORCE_ENV == "0":
        return False
    if _FORCE_ENV == "1":
        return True
    # No TTY → definitely not
    if not sys.stdout.isatty():
        return False
    term_prog = os.environ.get("TERM_PROGRAM", "").lower()
    if term_prog in {"iterm.app", "wezterm", "vscode", "foot"}:
        return True
    colorterm = os.environ.get("COLORTERM", "").lower()
    if colorterm in {"truecolor", "24bit"}:
        return True
    term = os.environ.get("TERM", "").lower()
    if "kitty" in term or "xterm" in term or "256color" in term:
        return True
    # Windows Terminal sets WT_SESSION
    if os.environ.get("WT_SESSION"):
        return True
    return False


def hyperlink(text: str, url: str) -> str:
    """Wrap *text* in an OSC-8 hyperlink to *url*.

    If OSC-8 is not supported, returns *text* unchanged.
    """
    if not osc8_supported():
        return text
    ESC = "\x1b"
    ST = "\x1b\\"
    return f"{ESC}]8;;{url}{ST}{text}{ESC}]8;;{ST}"


def file_hyperlink(
    file: str,
    line: int | None = None,
    *,
    repo_root: str | None = None,
    display: str | None = None,
) -> str:
    """Return an OSC-8 hyperlink for a source file reference.

    Args:
        file: Relative path to the file (e.g. ``src/api.py``).
        line: Optional line number.
        repo_root: Absolute path to the repository root; used to build
            a ``file://`` URI.  If *None*, falls back to ``os.getcwd()``.
        display: Display text override.  Defaults to ``file:line`` notation.

    Returns:
        OSC-8 hyperlink string, or plain ``file:line`` if not supported.
    """
    root = repo_root or str(Path.cwd())
    # Build file:// URI — resolve to absolute path
    abs_path = os.path.join(root, file) if not os.path.isabs(file) else file
    if line is not None:
        uri = f"file://{abs_path}#{line}"
        label = display or f"{file}:{line}"
    else:
        uri = f"file://{abs_path}"
        label = display or file

    return hyperlink(label, uri)


def print_citations(
    citations: list,  # list[Citation] — avoid circular import
    *,
    repo_root: str | None = None,
    console=None,
) -> None:
    """Print a formatted citations block with OSC-8 hyperlinks.

    Args:
        citations: List of ``Citation`` objects (from ``rekipedia.api``).
        repo_root: Absolute repo root for building ``file://`` URIs.
        console: Optional ``rich.console.Console`` instance.  If *None*,
            a fresh one is created.
    """
    if not citations:
        return

    if console is None:
        from rich.console import Console
        console = Console()

    console.print("\n[dim]─── Sources ───────────────────────────────────[/dim]")
    for i, cite in enumerate(citations, 1):
        link = file_hyperlink(cite.file, cite.line, repo_root=repo_root)
        snippet = f"  [dim]{cite.snippet}[/dim]" if cite.snippet else ""
        console.print(f"  [dim]{i}.[/dim] {link}{snippet}")
    console.print("[dim]──────────────────────────────────────────────[/dim]")
