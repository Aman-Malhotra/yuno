---
title: One `LLMProvider` ABC, One Impl per Provider
impact: HIGH
impactDescription: Agents are configured with `model_provider` + `model_name`; the runtime must dispatch to the right SDK behind a stable interface
tags: llm, providers, abstraction
---

## One `LLMProvider` ABC, One Impl per Provider

A single interface lets the runtime call any provider the same way. Adding a new provider is one file.

### Base interface

```python
# app/modules/llm/providers/base.py
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from pydantic import BaseModel


class LLMMessage(BaseModel):
    role: str
    content: str


class LLMToolCall(BaseModel):
    id: str
    name: str
    arguments: dict


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )


class LLMRequest(BaseModel):
    model: str
    messages: list[LLMMessage]
    temperature: float = 0.7
    max_tokens: int | None = None
    tools: list[dict] | None = None   # tool descriptors in provider-native shape


class LLMResponse(BaseModel):
    message: LLMMessage
    tool_calls: list[LLMToolCall] = []
    usage: TokenUsage = TokenUsage()
    raw: dict | None = None


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        ...

    @abstractmethod
    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        ...
```

### Provider impls

```txt
app/modules/llm/providers/
  base.py
  openai_provider.py
  anthropic_provider.py
  gemini_provider.py
  groq_provider.py
```

Use the official SDK per provider (`openai`, `anthropic`, `google-genai`, `groq`) — don't reimplement the HTTP API.

Sketch:

```python
# app/modules/llm/providers/openai_provider.py
from openai import AsyncOpenAI

from .base import LLMProvider, LLMRequest, LLMResponse, LLMMessage, LLMToolCall, TokenUsage


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def complete(self, request):
        resp = await self.client.chat.completions.create(
            model=request.model,
            messages=[m.model_dump() for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            tools=[{"type": "function", "function": t} for t in (request.tools or [])] or None,
        )
        choice = resp.choices[0]
        return LLMResponse(
            message=LLMMessage(role="assistant", content=choice.message.content or ""),
            tool_calls=[
                LLMToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(tc.function.arguments))
                for tc in (choice.message.tool_calls or [])
            ],
            usage=TokenUsage(
                input_tokens=resp.usage.prompt_tokens,
                output_tokens=resp.usage.completion_tokens,
            ),
            raw=resp.model_dump(),
        )

    async def stream(self, request):
        ...
```

### Registry + service

```python
# app/modules/llm/registry.py
from app.core.config import settings

from .providers.base import LLMProvider
from .providers.openai_provider import OpenAIProvider
from .providers.anthropic_provider import AnthropicProvider
from .providers.gemini_provider import GeminiProvider
from .providers.groq_provider import GroqProvider


def build_llm_registry() -> dict[str, LLMProvider]:
    reg: dict[str, LLMProvider] = {}
    if settings.openai_api_key:
        reg["openai"] = OpenAIProvider(settings.openai_api_key)
    if settings.anthropic_api_key:
        reg["anthropic"] = AnthropicProvider(settings.anthropic_api_key)
    if settings.gemini_api_key:
        reg["gemini"] = GeminiProvider(settings.gemini_api_key)
    if settings.groq_api_key:
        reg["groq"] = GroqProvider(settings.groq_api_key)
    return reg
```

```python
# app/modules/llm/service.py
class LLMService:
    def __init__(self, registry: dict[str, LLMProvider]):
        self.registry = registry

    async def complete(
        self,
        *,
        provider: str,
        model: str,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        impl = self.registry.get(provider)
        if impl is None:
            raise NotFoundError("provider_not_configured", f"provider {provider} not configured")
        return await impl.complete(LLMRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            tools=tools,
        ))
```

### Endpoints

```txt
GET /api/v1/llm-providers     -> list of available providers + their default models
```

The frontend uses this to populate the model picker. Never list providers that don't have an API key set.

### Bad — runtime imports the OpenAI SDK directly

```python
# ❌ Coupled to one provider, no way to swap
from openai import AsyncOpenAI

class AgentExecutor:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=...)
```

### Bad — agent stores raw API config

```python
# ❌ Each agent re-implements auth
agent.config = {"api_key": "...", "base_url": "..."}
```

API keys are global, in env / settings, never in the agent row.

### Adding a new provider (instructions for the README)

1. Add `<name>_provider.py` under `app/modules/llm/providers/`
2. Implement `LLMProvider` (`complete`, `stream`)
3. Add the env var(s) to `core/config.py`
4. Register in `build_llm_registry()` (gated on the env var)

### Rules

- One `LLMProvider` ABC; one impl per provider; one SDK per impl
- API keys live in `core/config.py` (from env), never on agent rows
- Registry built once at startup, gated by which env vars are set
- `LLMService.complete(provider=..., model=...)` is the only call site for the runtime
- Token usage flows back via `TokenUsage` so the runtime can emit + persist cost data

See: [[runtime-agent-executor]], [[tool-registry-interface]], [[ops-settings-pydantic]]
