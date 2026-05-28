from collections.abc import AsyncIterator

import pytest

from app.core.errors import NotFoundError
from app.modules.llm.configs.base import BaseLLMConfig
from app.modules.llm.configs.openai import OpenAIConfig
from app.modules.llm.factory import LLMFactory
from app.modules.llm.providers.base import LLMProvider
from app.modules.llm.providers.openai_provider import OpenAIProvider
from app.modules.llm.schemas import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
    TokenUsage,
)
from app.modules.llm.service import LLMService


class _FakeConfig(BaseLLMConfig):
    pass


class _FakeProvider(LLMProvider):
    name = "fake"

    def __init__(self, config: _FakeConfig) -> None:
        super().__init__(config)
        self.calls: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        return LLMResponse(
            message=LLMMessage(role="assistant", content=f"echo: {request.messages[-1].content}"),
            usage=TokenUsage(input_tokens=3, output_tokens=4),
            raw={"provider": "fake"},
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        async def _iter() -> AsyncIterator[str]:
            for token in ["he", "llo"]:
                yield token

        return _iter()


def test_supported_providers_includes_builtins() -> None:
    supported = LLMFactory.supported_providers()
    assert {"openai", "gemini", "groq"}.issubset(set(supported))


def test_unknown_provider_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        LLMFactory.create("nope", {"api_key": "x"})


def test_create_openai_from_dict_returns_provider() -> None:
    provider = LLMFactory.create("openai", {"api_key": "sk-test"})
    assert isinstance(provider, OpenAIProvider)
    assert provider.config.api_key == "sk-test"


def test_create_openai_from_config_instance() -> None:
    cfg = OpenAIConfig(api_key="sk-test", model="gpt-4o-mini", temperature=0.2)
    provider = LLMFactory.create("openai", cfg)
    assert isinstance(provider, OpenAIProvider)
    assert provider.config.model == "gpt-4o-mini"
    assert provider.config.temperature == pytest.approx(0.2)


async def test_register_custom_provider_and_use_via_service() -> None:
    LLMFactory.register("fake", f"{__name__}._FakeProvider", _FakeConfig)
    try:
        assert "fake" in LLMFactory.supported_providers()

        provider = LLMFactory.create("fake", {"api_key": "k"})
        assert isinstance(provider, _FakeProvider)

        service = LLMService(registry={"fake": provider})

        response = await service.complete(
            provider="fake",
            model="anything",
            messages=[LLMMessage(role="user", content="hi")],
        )
        assert response.message.content == "echo: hi"
        assert response.usage.input_tokens == 3
        assert response.usage.output_tokens == 4
    finally:
        LLMFactory.unregister("fake")


async def test_service_missing_provider_raises() -> None:
    service = LLMService(registry={})
    with pytest.raises(NotFoundError):
        await service.complete(
            provider="openai",
            model="x",
            messages=[LLMMessage(role="user", content="hi")],
        )
