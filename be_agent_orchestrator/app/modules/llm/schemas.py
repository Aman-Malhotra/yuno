from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

MessageRole = Literal["system", "user", "assistant", "tool"]


class LLMMessage(BaseModel):
    role: MessageRole
    # OpenAI/Groq allow ``content = null`` on an assistant turn when the
    # message only carries tool_calls. Keep it optional so the round-trip
    # works without sentinel values.
    content: str | None = None
    tool_call_id: str | None = None
    name: str | None = None
    # When the assistant requests tools, those calls live on this field
    # and must be re-sent to the provider in the next request so the tool
    # role messages we append can reference their ids.
    tool_calls: list["LLMToolCall"] | None = None


class LLMToolDescriptor(BaseModel):
    """Tool definition passed to the LLM (JSON Schema for arguments)."""

    name: str
    description: str
    parameters_schema: dict[str, Any]


class LLMToolCall(BaseModel):
    """Tool call requested by the model.

    Providers occasionally return ``arguments=null`` for zero-arg tool
    calls (seen on Groq). Coerce to ``{}`` at the schema boundary so the
    rest of the pipeline can treat arguments as a non-optional mapping.
    """

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)

    @field_validator("arguments", mode="before")
    @classmethod
    def _coerce_null_arguments(cls, value: Any) -> Any:
        return {} if value is None else value


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
    tools: list[LLMToolDescriptor] = Field(default_factory=list)
    tool_choice: Literal["auto", "none", "required"] = "auto"


class LLMResponse(BaseModel):
    message: LLMMessage
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    usage: TokenUsage = Field(default_factory=TokenUsage)
    raw: dict[str, Any] | None = None
