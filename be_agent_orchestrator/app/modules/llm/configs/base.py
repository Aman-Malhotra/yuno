from pydantic import BaseModel, ConfigDict


class BaseLLMConfig(BaseModel):
    """Common configuration shared across every LLM provider.

    Provider-specific subclasses add their own optional knobs (base_url,
    org id, model defaults, etc). All providers accept these base fields.
    """

    api_key: str
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    timeout_s: float = 60.0

    model_config = ConfigDict(extra="forbid", frozen=True)
