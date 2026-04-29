"""Thin litellm wrapper that honours LLMConfig and env-var overrides."""
from __future__ import annotations

import logging
import os
import time
from typing import Iterator

import litellm

from close_wiki.models.contracts import LLMConfig

logger = logging.getLogger("close_wiki.llm")

# Timeout per LLM call in seconds — wiki pages can be long, allow generous time
_DEFAULT_TIMEOUT = int(os.environ.get("CLOSE_WIKI_TIMEOUT", "180"))
# Max retry attempts on timeout / 5xx errors
_MAX_RETRIES = int(os.environ.get("CLOSE_WIKI_MAX_RETRIES", "3"))
# Retryable litellm exception types
_RETRYABLE = (
    litellm.Timeout,
    litellm.ServiceUnavailableError,
    litellm.InternalServerError,
    litellm.RateLimitError,
)


def _with_retry(fn, max_retries: int = _MAX_RETRIES):
    """Call *fn()* with exponential backoff on retryable errors."""
    delay = 5.0
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except _RETRYABLE as exc:
            if attempt == max_retries:
                raise
            wait = delay * (2 ** (attempt - 1))  # 5s, 10s, 20s
            logger.warning(
                "LLM call failed (%s: %s) — retrying in %.0fs (attempt %d/%d)",
                type(exc).__name__, exc, wait, attempt, max_retries,
            )
            time.sleep(wait)


class LLMClient:
    """Stateless LLM caller.  Thread-safe (litellm is stateless per call)."""

    def __init__(self, config: LLMConfig) -> None:
        # Env-var overrides take precedence over config file values
        self._model = os.environ.get("CLOSE_WIKI_MODEL") or config.model
        self._api_key = os.environ.get("CLOSE_WIKI_API_KEY") or config.api_key or None
        self._base_url = os.environ.get("CLOSE_WIKI_BASE_URL") or config.base_url or None
        self._temperature = config.temperature

    def _base_kwargs(self) -> dict:
        kwargs: dict = {
            "model": self._model,
            "temperature": self._temperature,
            "timeout": _DEFAULT_TIMEOUT,
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._base_url:
            kwargs["base_url"] = self._base_url
        return kwargs

    def call(self, prompt: str, *, system: str = "") -> str:
        """Send a prompt and return the assistant text.

        Retries up to ``_MAX_RETRIES`` times on timeout / 5xx errors.
        Raises ``litellm.exceptions.APIError`` on non-retryable upstream errors.
        """
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = {**self._base_kwargs(), "messages": messages}

        def _call():
            response = litellm.completion(**kwargs)
            return response.choices[0].message.content or ""

        return _with_retry(_call)

    def stream(self, prompt: str, *, system: str = "") -> Iterator[str]:
        """Stream response tokens as an iterator of text chunks.

        Yields each chunk's delta text as it arrives from the LLM.
        Raises ``litellm.exceptions.APIError`` on upstream errors.
        """
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = {**self._base_kwargs(), "messages": messages, "stream": True}
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._base_url:
            kwargs["base_url"] = self._base_url

        response = litellm.completion(**kwargs)
        for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
