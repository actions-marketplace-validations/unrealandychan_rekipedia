"""reki setup — interactive onboarding wizard (issue #144)."""
from __future__ import annotations

import click
import yaml

from rekipedia.config.loader import get_global_config_path

PROVIDERS: dict[str, dict] = {
    "OpenAI": {
        "models": ["gpt-4o", "gpt-4o-mini", "o3-mini"],
        "base_url": "",
        "needs_key": True,
        "model_prefix": "openai/",
    },
    "Anthropic": {
        "models": ["claude-sonnet-4-5", "claude-haiku-4-5", "claude-opus-4-5"],
        "base_url": "",
        "needs_key": True,
        "model_prefix": "anthropic/",
    },
    "Gemini (Google)": {
        "models": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"],
        "base_url": "",
        "needs_key": True,
        "model_prefix": "gemini/",
    },
    "Ollama (local)": {
        "models": ["llama4", "llama3.2", "mistral", "qwen2.5-coder"],
        "base_url": "http://localhost:11434",
        "needs_key": False,
        "model_prefix": "ollama/",
    },
    "OpenRouter": {
        "models": ["google/gemini-2.5-pro", "meta-llama/llama-4-maverick", "anthropic/claude-sonnet-4-5"],
        "base_url": "https://openrouter.ai/api/v1",
        "needs_key": True,
        "model_prefix": "openrouter/",
    },
    "Custom": {
        "models": [],
        "base_url": "",
        "needs_key": True,
        "model_prefix": "",
    },
}

_REQUIRED_PRESET_KEYS = {"models", "base_url", "needs_key", "model_prefix"}


@click.command("setup")
@click.option("--force", is_flag=True, default=False, help="Re-run even if global config already exists.")
@click.option("--no-test", "no_test", is_flag=True, default=False, help="Skip connection test.")
def setup_cmd(force: bool, no_test: bool) -> None:
    """Interactive onboarding wizard — configure global LLM settings."""
    config_path = get_global_config_path()

    click.echo("")
    click.echo("  ╭─ rekipedia setup ──────────────────────────────╮")
    click.echo("  │  Configure your global LLM settings.           │")
    click.echo(f"  │  Saved to {config_path!s:<37}│")
    click.echo("  ╰────────────────────────────────────────────────╯")
    click.echo("")

    if config_path.exists() and not force:
        overwrite = click.confirm(
            f"Global config already exists at {config_path}. Overwrite?",
            default=False,
        )
        if not overwrite:
            click.echo("Aborted.")
            return

    # --- Provider ---
    provider_names = list(PROVIDERS.keys())
    provider_name = click.prompt(
        "? LLM provider",
        type=click.Choice(provider_names, case_sensitive=False),
        default=provider_names[0],
    )
    preset = PROVIDERS[provider_name]

    # --- API Key ---
    api_key = ""
    if preset["needs_key"]:
        api_key = click.prompt("? API Key", hide_input=True, default="")

    # --- Base URL (for Custom provider) ---
    base_url = preset["base_url"]
    if provider_name == "Custom":
        base_url = click.prompt("? Base URL (OpenAI-compatible endpoint)", default="")

    # --- Model ---
    models = preset["models"]
    if provider_name in ("Ollama (local)", "Custom"):
        default_model = models[0] if models else ""
        raw_model = click.prompt("? Model", default=default_model)
        model = preset["model_prefix"] + raw_model if raw_model else ""
    else:
        raw_model = click.prompt(
            "? Model",
            type=click.Choice(models, case_sensitive=True),
            default=models[0] if models else "",
        )
        model = preset["model_prefix"] + raw_model

    # --- Build config dict ---
    llm_cfg: dict = {"model": model}
    if api_key:
        llm_cfg["api_key"] = api_key
    if base_url:
        llm_cfg["base_url"] = base_url

    config_data = {"llm": llm_cfg}

    # --- Write config ---
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.dump(config_data, default_flow_style=False))
    click.echo(f"✔ Saved to {config_path}")

    # --- Optional connection test ---
    if no_test:
        return

    run_test = click.confirm("? Test connection?", default=True)
    if not run_test:
        return

    from rekipedia.llm.client import LLMClient
    from rekipedia.models.contracts import LLMConfig

    click.echo("  Testing connection…", nl=False)
    try:
        llm_config = LLMConfig(
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
        result = LLMClient(llm_config).call("Say OK", system="Reply with just OK.")
        click.echo(f"\r✔ Connection OK — response: {result[:80]}")
    except Exception as exc:
        click.echo(f"\r✘ Connection failed: {exc}")
