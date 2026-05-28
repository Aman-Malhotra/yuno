from pydantic import ConfigDict

from app.modules.llm.configs.base import BaseLLMConfig


class OpenAIConfig(BaseLLMConfig):
    base_url: str | None = None
    organization: str | None = None
    default_model: str = "gpt-4o-mini"

    model_config = ConfigDict(extra="forbid", frozen=True)
