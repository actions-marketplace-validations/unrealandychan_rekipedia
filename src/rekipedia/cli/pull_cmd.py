"""reki pull — fetch and merge a remote wiki bundle."""
import json
import tempfile
from pathlib import Path

import click
from rich import print as rprint

from rekipedia.config.loader import load_config
from rekipedia.team_sync.transport import download_bundle, extract_bundle


@click.command("pull")
@click.argument("url", required=False, default=None)
@click.option("--output", "-o", default=".rekipedia/wiki", show_default=True, help="Local wiki dir to merge into")
@click.option("--dry-run", is_flag=True, default=False, help="Show what would change without writing")
def pull_cmd(url: str | None, output: str, dry_run: bool) -> None:
    """Fetch a remote wiki bundle and merge it into the local wiki.

    URL can be https://, s3://, or gs://. If omitted, reads team.remote_url from config.
    """
    from rekipedia.team_sync.merger import WikiMerger

    config = load_config(Path())
    team = config.get("team", {}) if isinstance(config, dict) else {}

    if not url:
        url = team.get("remote_url", "")
    if not url:
        raise click.UsageError("No URL provided and team.remote_url not set in .rekipedia/config.yml")

    local_wiki = Path(output)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        rprint(f"[cyan]Downloading[/] {url} ...")
        zip_path = download_bundle(url, tmp_path / "download")
        bundle_dir = extract_bundle(zip_path, tmp_path / "bundle")

        if dry_run:
            # Just show manifest without writing
            manifest_path = bundle_dir / "manifest.json"
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text())
                rprint(
                    f"[yellow]Dry run[/] — bundle_id: {manifest.get('bundle_id', '?')}, "
                    f"{len(manifest.get('pages', []))} pages"
                )
            else:
                rprint("[yellow]Dry run[/] — no manifest found in bundle")
            return

        # Find existing local bundle to use as base (if available)
        local_bundle = Path(".rekipedia/bundle")
        base = local_bundle if local_bundle.exists() and (local_bundle / "manifest.json").exists() else None

        out_dir = tmp_path / "merged"

        # If no local bundle, just copy remote directly
        if not local_bundle.exists():
            import shutil

            if (bundle_dir / "pages").exists():
                shutil.copytree(bundle_dir / "pages", local_wiki / "pages", dirs_exist_ok=True)
            if (bundle_dir / "diagrams").exists():
                shutil.copytree(bundle_dir / "diagrams", local_wiki / "diagrams", dirs_exist_ok=True)
            rprint(f"[green]Pulled[/] {url} → {local_wiki} (initial pull, no merge needed)")
            return

        merger = WikiMerger(bundle_dir, local_bundle, base=base)
        report = merger.merge(out_dir)
        report_dict = report.to_dict()
        s = report_dict["summary"]

        # Copy merged result to local wiki
        import shutil

        if (out_dir / "pages").exists():
            shutil.copytree(out_dir / "pages", local_wiki / "pages", dirs_exist_ok=True)
        if (out_dir / "diagrams").exists():
            shutil.copytree(out_dir / "diagrams", local_wiki / "diagrams", dirs_exist_ok=True)

        rprint(f"[green]Pull complete[/] → {local_wiki}")
        rprint(f"  clean: {s['clean']}  conflict: {s['conflict']}  added: {s['added']}  removed: {s['deleted']}")
        if report.merged_conflict:
            rprint(f"[yellow]Conflicts:[/] {', '.join(report.merged_conflict)}")
