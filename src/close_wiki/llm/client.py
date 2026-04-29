"""Thin litellm wrapper that honours LLMConfig and env-var overrides."""
from __future__ import annotations

import os
from typing import Iterator

import litellm

from close_wiki.models.contracts import LLMConfig


class LLMClient:
    """Stateless LLM caller.  Thread-safe (litellm is stateless per call)."""

    def __init__(self, config: LLMConfig) -> None:
        # Env-var overrides take precedence over config file values
        self._model = os.environ.get("CLOSE_WIKI_MODEL") or config.model
        self._api_key = os.environ.get("CLOSE_WIKI_API_KEY") or config.api_key or None
        self._base_url = os.environ.get("CLOSE_WIKI_BASE_URL") or config.base_url or None
        self._temperature = config.temperature

    def call(self, prompt: str, *, system: str = "") -> str:
        """Send a prompt and return the assistant text.

        Raises ``litellm.exceptions.APIError`` on upstream errors.
        """
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._base_url:
            kwargs["base_url"] = self._base_url

        response = litellm.completion(**kwargs)
        return response.choices[0].message.content or ""

    def stream(self, prompt: str, *, system: str = "") -> Iterator[str]:
        """Stream response tokens as an iterator of text chunks.

        Yields each chunk's delta text as it arrives from the LLM.
        Raises ``litellm.exceptions.APIError`` on upstream errors.
        """
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "stream": True,
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._base_url:
            kwargs["base_url"] = self._base_url

        response = litellm.completion(**kwargs)
        for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
