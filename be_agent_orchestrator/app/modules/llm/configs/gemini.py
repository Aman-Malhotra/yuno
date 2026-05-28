from pydantic import ConfigDict

from app.modules.llm.configs.base import BaseLLMConfig


class GeminiConfig(BaseLLMConfig):
    default_model: str = "gemini-2.0-flash"

    model_config = ConfigDict(extra="forbid", frozen=True)
