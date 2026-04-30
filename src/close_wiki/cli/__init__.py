"""close-wiki CLI entry point."""
from __future__ import annotations

import click

from close_wiki.cli.ask import ask_cmd
from close_wiki.cli.embed import embed_cmd
from close_wiki.cli.export import export_cmd
from close_wiki.cli.init import init_cmd
from close_wiki.cli.scan import scan_cmd
from close_wiki.cli.serve import serve_cmd
from close_wiki.cli.update import update_cmd


@click.group()
@click.version_option(package_name="close-wiki")
def main() -> None:
    """close-wiki — agentic repo-to-wiki knowledge store."""


main.add_command(init_cmd)
main.add_command(scan_cmd)
main.add_command(update_cmd)
main.add_command(ask_cmd)
main.add_command(embed_cmd)
main.add_command(export_cmd)
main.add_command(serve_cmd)
