"""rekipedia publish — copy wiki pages to a target output directory.

Usage:
    reki publish [REPO_PATH] [--output-dir PATH] [--format dir|zip] [--title TEXT] [--force]

Formats:
    dir  (default) — copy files into the target directory tree
    zip  — bundle everything into a single zip archive
"""
from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path

import click
from rich.console import Console

console = Console()

_FORMAT_CHOICES = click.Choice(["dir", "zip"], case_sensitive=False)


@click.command("publish")
@click.argument("repo_path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--output-dir",
    default=None,
    help="Destination directory (default: REPO_PATH/docs/wiki/).",
)
@click.option(
    "--format", "fmt",
    default="dir",
    type=_FORMAT_CHOICES,
    show_default=True,
    help="Output format: dir (copy files) or zip (bundle archive).",
)
@click.option(
    "--title",
    default=None,
    help="Title for the generated README index (default: repo directory name).",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite the target directory/zip if it already exists.",
)
def publish_cmd(
    repo_path: str,
    output_dir: str | None,
    fmt: str,
    title: str | None,
    force: bool,
) -> None:
    """Publish the wiki to a target output directory or zip bundle.

    \b
    Examples:
        reki publish .
        reki publish . --output-dir docs/wiki/
        reki publish . --format zip --output-dir site/wiki.zip --force
        reki publish . --title "My Project Wiki"
    """
    repo = Path(repo_path).resolve()
    reki_dir = repo / ".rekipedia"

    wiki_dir = reki_dir / "wiki"
    diagrams_dir = reki_dir / "diagrams"
    manifest_path = reki_dir / "exports" / "manifest.json"

    # -----------------------------------------------------------------------
    # Validate source
    # -----------------------------------------------------------------------
    if not wiki_dir.exists():
        console.print(
            f"[red]No wiki/ directory found at {wiki_dir}.[/red]\n"
            "Run [bold]reki scan[/bold] first."
        )
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Resolve output destination
    # -----------------------------------------------------------------------
    fmt = fmt.lower()

    if output_dir is not None:
        dest_root = Path(output_dir).resolve()
    else:
        dest_root = repo / "docs" / "wiki.zip" if fmt == "zip" else repo / "docs" / "wiki"

    # Guard against accidental overwrite
    if dest_root.exists() and not force:
        console.print(
            f"[yellow]Target already exists:[/yellow] [bold]{dest_root}[/bold]\n"
            "Use [bold]--force[/bold] to overwrite."
        )
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Load manifest metadata (optional)
    # -----------------------------------------------------------------------
    nav_order: list[str] = []
    pages_meta: dict[str, dict] = {}
    manifest_data: dict = {}

    if manifest_path.exists():
        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            nav_order = manifest_data.get("nav_order", [])
            for p in manifest_data.get("pages", []):
                pages_meta[p["slug"]] = p
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Collect & order wiki pages
    # -----------------------------------------------------------------------
    all_pages = sorted(wiki_dir.glob("*.md"))
    if nav_order:
        slug_map = {p.stem: p for p in all_pages}
        ordered = [slug_map[slug] for slug in nav_order if slug in slug_map]
        remaining = [p for p in all_pages if p.stem not in set(nav_order)]
        all_pages = ordered + remaining

    doc_title = title or repo.name

    # -----------------------------------------------------------------------
    # Dispatch to format handler
    # -----------------------------------------------------------------------
    if fmt == "zip":
        _publish_zip(
            pages=all_pages,
            diagrams_dir=diagrams_dir,
            manifest_path=manifest_path,
            dest=dest_root,
            title=doc_title,
            pages_meta=pages_meta,
            force=force,
        )
    else:
        _publish_dir(
            pages=all_pages,
            diagrams_dir=diagrams_dir,
            manifest_path=manifest_path,
            dest_root=dest_root,
            title=doc_title,
            pages_meta=pages_meta,
            force=force,
        )


# ---------------------------------------------------------------------------
# Format implementations
# ---------------------------------------------------------------------------

def _build_readme(title: str, pages: list[Path], pages_meta: dict[str, dict]) -> str:
    """Build a Markdown index README listing all wiki pages."""
    lines: list[str] = [
        f"# {title}\n",
        "\n",
        "> Generated by [rekipedia](https://github.com/unrealandychan/rekipedia).\n",
        "\n",
        "## Wiki Pages\n",
        "\n",
    ]
    for p in pages:
        slug = p.stem
        meta = pages_meta.get(slug, {})
        display_title = meta.get("title", slug.replace("-", " ").replace("_", " ").title())
        importance = meta.get("importance", "")
        section = meta.get("section", "")
        tags: list[str] = meta.get("tags", [])

        badge_parts: list[str] = []
        if section:
            badge_parts.append(f"section: `{section}`")
        if importance:
            badge_parts.append(f"importance: **{importance}**")
        if tags:
            badge_parts.append("tags: " + ", ".join(f"`{t}`" for t in tags))
        badge_str = f" — {' · '.join(badge_parts)}" if badge_parts else ""

        lines.append(f"- [{display_title}](wiki/{p.name}){badge_str}\n")

    lines.append("\n")
    return "".join(lines)


def _publish_dir(
    pages: list[Path],
    diagrams_dir: Path,
    manifest_path: Path,
    dest_root: Path,
    title: str,
    pages_meta: dict[str, dict],
    force: bool,
) -> None:
    """Copy files into a structured output directory."""
    wiki_out = dest_root / "wiki"
    diagrams_out = dest_root / "diagrams"

    # Clean existing target if --force
    if dest_root.exists() and force:
        shutil.rmtree(dest_root)

    wiki_out.mkdir(parents=True, exist_ok=True)

    copied_wiki: list[Path] = []
    copied_diagrams: list[Path] = []

    # Copy wiki pages
    for src in pages:
        dst = wiki_out / src.name
        shutil.copy2(src, dst)
        copied_wiki.append(dst)

    # Copy diagrams
    if diagrams_dir.exists():
        diagrams_out.mkdir(parents=True, exist_ok=True)
        for src in sorted(diagrams_dir.glob("*.md")):
            dst = diagrams_out / src.name
            shutil.copy2(src, dst)
            copied_diagrams.append(dst)

    # Copy manifest
    manifest_copied = False
    if manifest_path.exists():
        shutil.copy2(manifest_path, dest_root / "manifest.json")
        manifest_copied = True

    # Write README index
    readme_content = _build_readme(title, pages, pages_meta)
    readme_path = dest_root / "README.md"
    readme_path.write_text(readme_content, encoding="utf-8")

    # Summary
    console.print(f"\n[green bold]✅ Published wiki → {dest_root}[/green bold]\n")
    console.print(f"  [cyan]wiki pages  :[/cyan] {len(copied_wiki)}")
    if copied_diagrams:
        console.print(f"  [cyan]diagrams    :[/cyan] {len(copied_diagrams)}")
    if manifest_copied:
        console.print("  [cyan]manifest    :[/cyan] manifest.json")
    console.print("  [cyan]index       :[/cyan] README.md")
    console.print(
        f"\n[dim]Open [bold]{readme_path}[/bold] to browse the wiki.[/dim]\n"
    )


def _publish_zip(
    pages: list[Path],
    diagrams_dir: Path,
    manifest_path: Path,
    dest: Path,
    title: str,
    pages_meta: dict[str, dict],
    force: bool,
) -> None:
    """Bundle wiki files into a zip archive."""
    if dest.exists() and force:
        dest.unlink()

    dest.parent.mkdir(parents=True, exist_ok=True)

    readme_content = _build_readme(title, pages, pages_meta)

    n_wiki = 0
    n_diagrams = 0
    has_manifest = False

    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # README at archive root
        zf.writestr("README.md", readme_content)

        # Wiki pages
        for src in pages:
            zf.write(src, arcname=f"wiki/{src.name}")
            n_wiki += 1

        # Diagrams
        if diagrams_dir.exists():
            for src in sorted(diagrams_dir.glob("*.md")):
                zf.write(src, arcname=f"diagrams/{src.name}")
                n_diagrams += 1

        # Manifest
        if manifest_path.exists():
            zf.write(manifest_path, arcname="manifest.json")
            has_manifest = True

    size_kb = dest.stat().st_size / 1024

    console.print(f"\n[green bold]✅ Published wiki → {dest}[/green bold]\n")
    console.print(f"  [cyan]wiki pages  :[/cyan] {n_wiki}")
    if n_diagrams:
        console.print(f"  [cyan]diagrams    :[/cyan] {n_diagrams}")
    if has_manifest:
        console.print("  [cyan]manifest    :[/cyan] manifest.json")
    console.print("  [cyan]index       :[/cyan] README.md")
    console.print(f"  [cyan]archive size:[/cyan] {size_kb:.1f} KB")
    console.print(
        "\n[dim]Extract and open [bold]README.md[/bold] to browse the wiki.[/dim]\n"
    )
