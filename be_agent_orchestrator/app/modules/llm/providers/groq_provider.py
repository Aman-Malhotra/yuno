import json
from collections.abc import AsyncIterator
from typing import Any, cast

from groq import AsyncGroq

from app.modules.llm.configs.groq import GroqConfig
from app.modules.llm.providers.base import LLMProvider
from app.modules.llm.schemas import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMToolDescriptor,
    TokenUsage,
)


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self, config: GroqConfig) -> None:
        super().__init__(config)
        self._typed_config: GroqConfig = config
        self.client = AsyncGroq(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_s,
        )

    def _resolve_model(self, request_model: str) -> str:
        return request_model or self._typed_config.model or self._typed_config.default_model

    @staticmethod
    def _to_groq_messages(messages: list[LLMMessage]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in messages:
            # `content` is nullable on assistant turns that only carry tool_calls;
            # the SDK serializes `None` to JSON null which Groq accepts here.
            entry: dict[str, Any] = {"role": m.role, "content": m.content}
            if m.role == "tool":
                if not m.tool_call_id:
                    raise ValueError("tool messages must include tool_call_id")
                entry["tool_call_id"] = m.tool_call_id
            if m.name:
                entry["name"] = m.name
            if m.role == "assistant" and m.tool_calls:
                # Round-trip the tool_calls so subsequent `tool` messages
                # can reference them by id.
                entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in m.tool_calls
                ]
            out.append(entry)
        return out

    @staticmethod
    def _to_groq_tools(tools: list[LLMToolDescriptor]) -> list[dict[str, Any]] | None:
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
    def _parse_tool_calls(message: Any) -> list[LLMToolCall]:
        raw_calls = getattr(message, "tool_calls", None) or []
        parsed: list[LLMToolCall] = []
        for tc in raw_calls:
            try:
                arguments: dict[str, Any] = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {"_raw": tc.function.arguments}
            parsed.append(LLMToolCall(id=tc.id, name=tc.function.name, arguments=arguments))
        return parsed

    async def complete(self, request: LLMRequest) -> LLMResponse:
        # Groq SDK mirrors OpenAI's TypedDict params; cast at the boundary.
        # Passing ``tool_choice=None`` serializes to JSON ``null`` which
        # Groq rejects (only "none"/"auto"/"required" allowed). When there
        # are no tools, omit the kwarg entirely.
        kwargs: dict[str, Any] = {
            "model": self._resolve_model(request.model),
            "messages": cast(Any, self._to_groq_messages(request.messages)),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        groq_tools = self._to_groq_tools(request.tools)
        if groq_tools is not None:
            kwargs["tools"] = cast(Any, groq_tools)
            kwargs["tool_choice"] = cast(Any, request.tool_choice)

        completion = await self.client.chat.completions.create(**kwargs)

        choice = completion.choices[0]
        content = choice.message.content or ""
        usage = TokenUsage(
            input_tokens=completion.usage.prompt_tokens if completion.usage else 0,
            output_tokens=completion.usage.completion_tokens if completion.usage else 0,
        )

        return LLMResponse(
            message=LLMMessage(role="assistant", content=content),
            tool_calls=self._parse_tool_calls(choice.message),
            usage=usage,
            raw=completion.model_dump() if hasattr(completion, "model_dump") else None,
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        stream: Any = await self.client.chat.completions.create(
            model=self._resolve_model(request.model),
            messages=cast(Any, self._to_groq_messages(request.messages)),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True,
        )

        async def _iter() -> AsyncIterator[str]:
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta

        return _iter()
