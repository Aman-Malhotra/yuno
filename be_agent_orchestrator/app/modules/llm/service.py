from collections.abc import AsyncIterator

from app.core.errors import NotFoundError
from app.modules.llm.providers.base import LLMProvider
from app.modules.llm.schemas import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMToolDescriptor,
)


class LLMService:
    """High-level entry point for the agent runtime.

    Routes by provider name, delegates to the registered provider,
    keeps the call site stable regardless of which provider is in use.
    """

    def __init__(self, registry: dict[str, LLMProvider]) -> None:
        self.registry = registry

    def provider(self, name: str) -> LLMProvider:
        provider = self.registry.get(name)
        if provider is None:
            raise NotFoundError(
                "provider_not_configured",
                f"LLM provider {name!r} is not configured (no API key set)",
                {"configured": sorted(self.registry.keys())},
            )
        return provider

    def configured_providers(self) -> list[str]:
        return sorted(self.registry.keys())

    async def complete(
        self,
        *,
        provider: str,
        model: str,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[LLMToolDescriptor] | None = None,
    ) -> LLMResponse:
        impl = self.provider(provider)
        request = LLMRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools or [],
        )
        return await impl.complete(request)

    async def stream(
        self,
        *,
        provider: str,
        model: str,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        impl = self.provider(provider)
        request = LLMRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return await impl.stream(request)
