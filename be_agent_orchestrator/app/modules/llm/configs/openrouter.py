"""OpenRouter config.

OpenRouter (https://openrouter.ai) proxies many providers (OpenAI, Anthropic,
Google, Meta, Mistral, …) behind a single OpenAI-compatible endpoint. Keys
are workspace-scoped just like any other provider in this app; the only
real difference at the API surface is the base URL.

Optional `http_referer` + `app_title` are OpenRouter-specific headers that
attribute usage in their dashboard (and improve free-tier rate limits).
They're harmless to leave unset.
"""

from pydantic import ConfigDict, Field

from app.modules.llm.configs.base import BaseLLMConfig


class OpenRouterConfig(BaseLLMConfig):
    base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter's OpenAI-compatible endpoint. Override only for proxies.",
    )
    default_model: str = Field(
        default="openrouter/auto",
        description="Default routing target. `openrouter/auto` picks per request; "
        "`openrouter/free` constrains to free models only.",
    )
    http_referer: str | None = Field(
        default=None,
        description="Optional HTTP-Referer header for OpenRouter attribution.",
    )
    app_title: str | None = Field(
        default=None,
        description="Optional X-Title header. Shows up in the OpenRouter dashboard.",
    )

    model_config = ConfigDict(extra="forbid", frozen=True)
