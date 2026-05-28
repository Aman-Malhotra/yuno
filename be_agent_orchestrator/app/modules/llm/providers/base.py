from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.modules.llm.configs.base import BaseLLMConfig
from app.modules.llm.schemas import LLMRequest, LLMResponse


class LLMProvider(ABC):
    """Interface every LLM provider implements.

    Implementations construct their SDK client from the typed config and
    expose two methods:

    - ``complete``: one-shot non-streaming chat completion. Returns the
      full ``LLMResponse`` including any tool calls and token usage.
    - ``stream``: async iterator over content chunks. Tool calls are not
      streamed — if the model wants to call a tool, prefer ``complete``.
    """

    name: str

    def __init__(self, config: BaseLLMConfig) -> None:
        self.config = config
        self._validate()

    def _validate(self) -> None:
        if not self.config.api_key:
            raise ValueError(f"{self.__class__.__name__}: api_key is required")

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    async def stream(self, request: LLMRequest) -> AsyncIterator[str]: ...
