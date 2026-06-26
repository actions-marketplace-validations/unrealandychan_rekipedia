"""`rekipedia serve` command — local web UI."""
from __future__ import annotations

import os
import webbrowser
from pathlib import Path

import click

from rekipedia.models.contracts import LLMConfig


@click.command("serve")
@click.option(
    "--repo",
    default=".",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Repository root (default: current directory).",
)
@click.option("--port", default=7070, show_default=True, help="Port to listen on.")
@click.option("--host", default="127.0.0.1", show_default=True, help="Host to bind to.")
@click.option("--output-dir", default=None, type=click.Path(path_type=Path))
@click.option("--model", default=None, envvar="REKIPEDIA_MODEL")
@click.option("--open/--no-open", "open_browser", default=True, help="Auto-open browser.")
@click.option(
    "--title",
    default=None,
    help="Custom project title shown in the web UI (overrides repo name).",
    envvar="REKI_TITLE",
)
@click.option(
    "--logo",
    default=None,
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to a custom logo image (PNG/SVG/JPEG) to display in the web UI.",
    envvar="REKI_LOGO",
)
def serve_cmd(
    repo: Path,
    port: int,
    host: str,
    output_dir: Path | None,
    model: str | None,
    open_browser: bool,
    title: str | None,
    logo: str | None,
) -> None:
    """Start the rekipedia web UI.

    \b
    Examples:
        rekipedia serve
        rekipedia serve --port 8080
        rekipedia serve --repo ./my-project --no-open
        rekipedia serve --title "My Project" --logo ./logo.png
    """
    import uvicorn

    repo = repo.resolve()
    output_dir = (output_dir or repo / ".rekipedia").resolve()

    from rekipedia.config.loader import load_config
    cfg = load_config(repo)
    llm_raw = cfg.get("llm", {}) if isinstance(cfg, dict) else {}
    llm_config = LLMConfig(
        model=os.environ.get("REKIPEDIA_MODEL") or model or llm_raw.get("model", "ollama/llama4"),
        api_key=os.environ.get("REKIPEDIA_API_KEY") or llm_raw.get("api_key", ""),
        base_url=os.environ.get("REKIPEDIA_BASE_URL") or llm_raw.get("base_url", ""),
        temperature=llm_raw.get("temperature", 0.2),
    )

    # Resolve custom title / logo
    custom_title: str | None = title or (cfg.get("serve", {}) or {}).get("title") if isinstance(cfg, dict) else title
    custom_logo: Path | None = None
    raw_logo = logo or (cfg.get("serve", {}) or {}).get("logo") if isinstance(cfg, dict) else logo
    if raw_logo:
        custom_logo = Path(raw_logo).resolve()

    from rekipedia.server.app import create_app

    app = create_app(
        repo_root=repo,
        output_dir=output_dir,
        llm_config=llm_config,
        custom_title=custom_title,
        custom_logo=custom_logo,
    )

    url = f"http://{host}:{port}"
    click.echo(f"  rekipedia serve → {url}")
    click.echo(f"  repo       : {repo}")
    click.echo(f"  output-dir : {output_dir}")
    click.echo(f"  model      : {llm_config.model}")
    if custom_title:
        click.echo(f"  title      : {custom_title}")
    if custom_logo:
        click.echo(f"  logo       : {custom_logo}")

    if open_browser:
        import threading

        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    uvicorn.run(app, host=host, port=port, log_level="warning")
