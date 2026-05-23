import click


@click.command('mcp')
@click.option('--output-dir', default='.', show_default=True)
def mcp_cmd(output_dir):
    """Start MCP stdio server exposing rekipedia tools."""
    from rekipedia.cli.mcp_server import run_mcp_server
    run_mcp_server(output_dir)
