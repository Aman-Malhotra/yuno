from collections.abc import AsyncIterator
from typing import Any

from google import genai
from google.genai import types as genai_types

from app.modules.llm.configs.gemini import GeminiConfig
from app.modules.llm.providers.base import LLMProvider
from app.modules.llm.schemas import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMToolDescriptor,
    TokenUsage,
)


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, config: GeminiConfig) -> None:
        super().__init__(config)
        self._typed_config: GeminiConfig = config
        self.client = genai.Client(api_key=config.api_key)

    def _resolve_model(self, request_model: str) -> str:
        return request_model or self._typed_config.model or self._typed_config.default_model

    @staticmethod
    def _to_gemini_contents(
        messages: list[LLMMessage],
    ) -> tuple[str | None, list[genai_types.Content]]:
        """Split a chat-style message list into Gemini's (system, contents) form.

        Gemini uses `system_instruction` for the system prompt and an
        ordered list of contents for the conversation. Tool result messages
        are encoded as `function_response` parts.
        """
        system_text: str | None = None
        contents: list[genai_types.Content] = []
        for m in messages:
            # `content` is now Optional on LLMMessage (assistant turns with
            # only tool_calls carry no text). Coalesce to "" so the Gemini
            # encoder stays string-typed.
            text = m.content or ""
            if m.role == "system":
                system_text = (system_text + "\n" if system_text else "") + text
                continue

            role = "user" if m.role in ("user", "tool") else "model"
            if m.role == "tool":
                if not m.name:
                    raise ValueError("tool messages must include name for Gemini")
                part = genai_types.Part.from_function_response(
                    name=m.name,
                    response={"result": text},
                )
            else:
                part = genai_types.Part.from_text(text=text)
            contents.append(genai_types.Content(role=role, parts=[part]))
        return system_text, contents

    @staticmethod
    def _to_gemini_tools(
        tools: list[LLMToolDescriptor],
    ) -> list[genai_types.Tool] | None:
        if not tools:
            return None
        declarations: list[genai_types.FunctionDeclaration] = [
            genai_types.FunctionDeclaration(
                name=t.name,
                description=t.description,
                parameters=t.parameters_schema,
            )
            for t in tools
        ]
        return [genai_types.Tool(function_declarations=declarations)]

    @staticmethod
    def _parse_tool_calls(response: Any) -> list[LLMToolCall]:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return []
        parts = getattr(candidates[0].content, "parts", None) or []
        calls: list[LLMToolCall] = []
        for idx, part in enumerate(parts):
            fc = getattr(part, "function_call", None)
            if fc is None:
                continue
            calls.append(
                LLMToolCall(
                    id=f"call_{idx}",
                    name=fc.name,
                    arguments=dict(fc.args) if fc.args else {},
                )
            )
        return calls

    @staticmethod
    def _extract_text(response: Any) -> str:
        text = getattr(response, "text", None)
        if isinstance(text, str):
            return text
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return ""
        parts = getattr(candidates[0].content, "parts", None) or []
        return "".join(getattr(p, "text", "") or "" for p in parts)

    @staticmethod
    def _extract_usage(response: Any) -> TokenUsage:
        meta = getattr(response, "usage_metadata", None)
        if meta is None:
            return TokenUsage()
        return TokenUsage(
            input_tokens=getattr(meta, "prompt_token_count", 0) or 0,
            output_tokens=getattr(meta, "candidates_token_count", 0) or 0,
        )

    async def complete(self, request: LLMRequest) -> LLMResponse:
        system_text, contents = self._to_gemini_contents(request.messages)
        tools = self._to_gemini_tools(request.tools)

        config = genai_types.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
            system_instruction=system_text,
            tools=tools,
        )

        response = await self.client.aio.models.generate_content(
            model=self._resolve_model(request.model),
            contents=contents,
            config=config,
        )

        return LLMResponse(
            message=LLMMessage(role="assistant", content=self._extract_text(response)),
            tool_calls=self._parse_tool_calls(response),
            usage=self._extract_usage(response),
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        system_text, contents = self._to_gemini_contents(request.messages)
        config = genai_types.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
            system_instruction=system_text,
        )

        stream = await self.client.aio.models.generate_content_stream(
            model=self._resolve_model(request.model),
            contents=contents,
            config=config,
        )

        async def _iter() -> AsyncIterator[str]:
            async for chunk in stream:
                text = self._extract_text(chunk)
                if text:
                    yield text

        return _iter()
