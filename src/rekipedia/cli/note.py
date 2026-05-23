"""CLI commands for tech lead notes: reki note add/list/remove/edit/import."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import click
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from rekipedia.storage.sqlite_store import SqliteStore


def _get_store(ctx: click.Context) -> tuple[SqliteStore, Path]:
    """Resolve the store from context or CWD."""
    repo_root = Path(ctx.obj.get("repo_root", ".")).resolve() if ctx.obj else Path().resolve()
    output_dir = repo_root / ".rekipedia"
    db_path = output_dir / "store.db"
    store = SqliteStore(db_path)
    store.open()
    return store, repo_root


@click.group(name="note")
def note_cmd() -> None:
    """Manage tech lead notes."""


@note_cmd.command("add")
@click.argument("content")
@click.option("--tag", default="", help="Comma-separated tags, e.g. ops,auth")
@click.pass_context
def note_add(ctx: click.Context, content: str, tag: str) -> None:
    """Add a new tech lead note."""
    store, _ = _get_store(ctx)
    try:
        nid = store.upsert_note(content=content, tags=tag, source="manual")
        click.echo(f"Note added: {nid}")
    finally:
        store.close()


@note_cmd.command("list")
@click.option("--tag", default=None, help="Filter by tag")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON array")
@click.pass_context
def note_list(ctx: click.Context, tag: str | None, as_json: bool) -> None:
    """List tech lead notes."""
    store, _ = _get_store(ctx)
    try:
        notes = store.list_notes(tags=tag)
        if as_json:
            click.echo(json.dumps(notes, indent=2))
        else:
            if not notes:
                click.echo("No notes found.")
                return
            for n in notes:
                tags_display = f"[{n['tags']}] " if n["tags"] else ""
                click.echo(f"{n['id'][:8]}  {tags_display}{n['content'][:80]}")
    finally:
        store.close()


@note_cmd.command("remove")
@click.argument("note_id")
@click.pass_context
def note_remove(ctx: click.Context, note_id: str) -> None:
    """Remove a note by ID (or ID prefix)."""
    store, _ = _get_store(ctx)
    try:
        # Support prefix matching
        notes = store.list_notes()
        matches = [n for n in notes if n["id"].startswith(note_id)]
        if not matches:
            click.echo(f"No note found with id starting with '{note_id}'", err=True)
            sys.exit(1)
        if len(matches) > 1:
            click.echo(f"Ambiguous id prefix '{note_id}' matches {len(matches)} notes", err=True)
            sys.exit(1)
        deleted = store.delete_note(matches[0]["id"])
        if deleted:
            click.echo(f"Deleted note {matches[0]['id']}")
        else:
            click.echo("Note not found.", err=True)
    finally:
        store.close()


@note_cmd.command("edit")
@click.argument("note_id")
@click.option("--content", default=None, help="New content (skips editor)")
@click.pass_context
def note_edit(ctx: click.Context, note_id: str, content: str | None) -> None:
    """Edit a note. Opens $EDITOR if --content not provided."""
    store, _ = _get_store(ctx)
    try:
        notes = store.list_notes()
        matches = [n for n in notes if n["id"].startswith(note_id)]
        if not matches:
            click.echo(f"No note found with id starting with '{note_id}'", err=True)
            sys.exit(1)
        note = matches[0]

        if content is None:
            editor = os.environ.get("EDITOR", "vi")
            with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
                f.write(note["content"])
                tmp_path = f.name
            subprocess.call([editor, tmp_path])
            content = Path(tmp_path).read_text()
            os.unlink(tmp_path)

        store.upsert_note(content=content, tags=note["tags"], source=note["source"],
                          note_id=note["id"])
        click.echo(f"Updated note {note['id']}")
    finally:
        store.close()


@note_cmd.command("import")
@click.argument("file", type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True, default=False, help="Print what would be imported")
@click.pass_context
def note_import(ctx: click.Context, file: str, dry_run: bool) -> None:
    """Import notes from a YAML or Markdown file."""
    from rekipedia.notes.importer import import_notes_from_file
    store, _ = _get_store(ctx)
    try:
        notes = import_notes_from_file(Path(file))
        if not notes:
            click.echo("No notes found in file.")
            return

        # Dedup: skip notes with identical content
        existing = store.list_notes()
        existing_contents = {n["content"] for n in existing}
        new_notes = [n for n in notes if n["content"] not in existing_contents]
        skipped = len(notes) - len(new_notes)

        if dry_run:
            click.echo(f"Would import {len(new_notes)} note(s) (skipping {skipped} duplicates):")
            for n in new_notes:
                click.echo(f"  [{n.get('tags','')}] {n['content'][:60]}")
            return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task("Importing notes…", total=len(new_notes))
            for n in new_notes:
                store.upsert_note(content=n["content"], tags=n.get("tags", ""), source="import")
                progress.advance(task)

        click.echo(f"Imported {len(new_notes)} note(s) (skipped {skipped} duplicates).")
    finally:
        store.close()
