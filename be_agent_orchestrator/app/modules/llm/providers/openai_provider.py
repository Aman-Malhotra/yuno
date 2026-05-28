import json
from collections.abc import AsyncIterator
from typing import Any, cast

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

from app.modules.llm.configs.openai import OpenAIConfig
from app.modules.llm.providers.base import LLMProvider
from app.modules.llm.schemas import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMToolDescriptor,
    TokenUsage,
)


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, config: OpenAIConfig) -> None:
        super().__init__(config)
        self._typed_config: OpenAIConfig = config
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            organization=config.organization,
            timeout=config.timeout_s,
        )

    def _resolve_model(self, request_model: str) -> str:
        return request_model or self._typed_config.model or self._typed_config.default_model

    @staticmethod
    def _to_openai_messages(
        messages: list[LLMMessage],
    ) -> list[ChatCompletionMessageParam]:
        out: list[ChatCompletionMessageParam] = []
        for m in messages:
            entry: dict[str, Any] = {"role": m.role, "content": m.content}
            if m.role == "tool":
                if not m.tool_call_id:
                    raise ValueError("tool messages must include tool_call_id")
                entry["tool_call_id"] = m.tool_call_id
            if m.name:
                entry["name"] = m.name
            out.append(cast(ChatCompletionMessageParam, entry))
        return out

    @staticmethod
    def _to_openai_tools(tools: list[LLMToolDescriptor]) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters_schema,
                },
            }
            for t in tools
        ]

    @staticmethod
    def _parse_tool_calls(completion: ChatCompletion) -> list[LLMToolCall]:
        choice = completion.choices[0]
        raw_tool_calls = choice.message.tool_calls or []
        parsed: list[LLMToolCall] = []
        for tc in raw_tool_calls:
            # Custom tool calls (non-function) have no `.function` attribute; skip.
            fn = getattr(tc, "function", None)
            if fn is None:
                continue
            try:
                arguments: dict[str, Any] = json.loads(fn.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {"_raw": fn.arguments}
            parsed.append(LLMToolCall(id=tc.id, name=fn.name, arguments=arguments))
        return parsed

    async def complete(self, request: LLMRequest) -> LLMResponse:
        # OpenAI SDK uses TypedDict params; we produce valid runtime shapes
        # from Pydantic models, so cast at the boundary.
        completion = await self.client.chat.completions.create(
            model=self._resolve_model(request.model),
            messages=self._to_openai_messages(request.messages),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            tools=cast(Any, self._to_openai_tools(request.tools)),
            tool_choice=cast(Any, request.tool_choice if request.tools else None),
        )

        choice = completion.choices[0]
        content = choice.message.content or ""
        usage = TokenUsage(
            input_tokens=completion.usage.prompt_tokens if completion.usage else 0,
            output_tokens=completion.usage.completion_tokens if completion.usage else 0,
        )

        return LLMResponse(
            message=LLMMessage(role="assistant", content=content),
            tool_calls=self._parse_tool_calls(completion),
            usage=usage,
            raw=completion.model_dump(),
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        stream: Any = await self.client.chat.completions.create(
            model=self._resolve_model(request.model),
            messages=self._to_openai_messages(request.messages),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True,
        )

        async def _iter() -> AsyncIterator[str]:
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta

        return _iter()
