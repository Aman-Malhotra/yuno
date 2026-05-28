"""OpenRouter provider — thin shell over OpenAIProvider.

OpenRouter's API is OpenAI-compatible (same chat/completions schema,
same tool-call shape), so we reuse the entire OpenAI adapter and only
override the client construction:

  * base_url pinned to OpenRouter
  * Optional ``HTTP-Referer`` + ``X-Title`` headers for attribution

Tool calling, streaming, message shaping — all inherited unchanged.
"""

from __future__ import annotations

from openai import AsyncOpenAI

from app.modules.llm.configs.openrouter import OpenRouterConfig
from app.modules.llm.providers.openai_provider import OpenAIProvider


class OpenRouterProvider(OpenAIProvider):
    name = "openrouter"

    def __init__(self, config: OpenRouterConfig) -> None:
        # Skip OpenAIProvider.__init__ — we need different client headers.
        # Call the base LLMProvider init by hand so the abstract layer's
        # invariants still hold.
        super(OpenAIProvider, self).__init__(config)
        # Mypy can't narrow self._typed_config through the super chain;
        # we read OpenRouter-specific fields directly off `config`.
        self._typed_config: OpenRouterConfig = config  # type: ignore[assignment]

        default_headers: dict[str, str] = {}
        if config.http_referer:
            default_headers["HTTP-Referer"] = config.http_referer
        if config.app_title:
            default_headers["X-Title"] = config.app_title

        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_s,
            default_headers=default_headers or None,
        )
