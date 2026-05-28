from pydantic import ConfigDict

from app.modules.llm.configs.base import BaseLLMConfig


class GroqConfig(BaseLLMConfig):
    base_url: str | None = None
    default_model: str = "llama-3.3-70b-versatile"

    model_config = ConfigDict(extra="forbid", frozen=True)
