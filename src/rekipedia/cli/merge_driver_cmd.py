"""reki merge-driver — git merge driver for wiki pages."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import click


@click.command("merge-driver")
@click.argument("base", type=click.Path())
@click.argument("ours", type=click.Path(exists=True))
@click.argument("theirs", type=click.Path(exists=True))
def merge_driver_cmd(base: str, ours: str, theirs: str) -> None:
    """Git merge driver: merge OURS and THEIRS wiki pages with BASE as ancestor.

    Exits 0 on clean merge, 1 on conflict (writes best-effort result to OURS).
    This command is invoked automatically by git when .gitattributes specifies merge=reki-wiki.
    """
    from rekipedia.team_sync.merger import CONFLICT_MARKER

    base_path = Path(base)
    ours_path = Path(ours)
    theirs_path = Path(theirs)

    ours_content = ours_path.read_text(encoding="utf-8")
    theirs_content = theirs_path.read_text(encoding="utf-8")
    base_content = base_path.read_text(encoding="utf-8") if base_path.exists() else ""

    def strip_hash(text: str) -> str:
        lines = text.splitlines()
        return "\n".join(line for line in lines if not line.startswith("<!-- reki:hash:"))

    h_ours = hashlib.sha256(strip_hash(ours_content).encode()).hexdigest()[:16]
    h_theirs = hashlib.sha256(strip_hash(theirs_content).encode()).hexdigest()[:16]
    h_base = hashlib.sha256(strip_hash(base_content).encode()).hexdigest()[:16] if base_content else None

    if h_ours == h_theirs:
        # identical — no-op
        sys.exit(0)

    if h_base and h_ours == h_base:
        # only theirs changed — take theirs
        ours_path.write_text(theirs_content, encoding="utf-8")
        sys.exit(0)

    if h_base and h_theirs == h_base:
        # only ours changed — keep ours
        sys.exit(0)

    # both changed — write conflict markers into OURS, exit 1
    conflict = (
        f"{CONFLICT_MARKER}\n"
        f"<!-- reki:conflict:ours -->\n"
        f"{ours_content}\n"
        f"<!-- reki:conflict:theirs -->\n"
        f"{theirs_content}\n"
    )
    ours_path.write_text(conflict, encoding="utf-8")
    sys.exit(1)
