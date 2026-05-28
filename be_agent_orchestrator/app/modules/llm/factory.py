import importlib
from typing import Any

from app.modules.llm.configs.base import BaseLLMConfig
from app.modules.llm.configs.gemini import GeminiConfig
from app.modules.llm.configs.groq import GroqConfig
from app.modules.llm.configs.openai import OpenAIConfig
from app.modules.llm.configs.openrouter import OpenRouterConfig
from app.modules.llm.providers.base import LLMProvider

ProviderEntry = tuple[str, type[BaseLLMConfig]]


def _load_class(class_path: str) -> type[LLMProvider]:
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls: Any = getattr(module, class_name)
    if not isinstance(cls, type) or not issubclass(cls, LLMProvider):
        raise TypeError(f"{class_path} is not an LLMProvider subclass")
    return cls


class LLMFactory:
    """Factory for building LLMProvider instances from a name + config.

    Mirrors the mem0 pattern: a single dict maps provider name to
    (class_path, ConfigClass). New providers register without touching
    any other module.
    """

    _registry: dict[str, ProviderEntry] = {
        "openai": ("app.modules.llm.providers.openai_provider.OpenAIProvider", OpenAIConfig),
        "gemini": ("app.modules.llm.providers.gemini_provider.GeminiProvider", GeminiConfig),
        "groq": ("app.modules.llm.providers.groq_provider.GroqProvider", GroqConfig),
        "openrouter": (
            "app.modules.llm.providers.openrouter_provider.OpenRouterProvider",
            OpenRouterConfig,
        ),
    }

    @classmethod
    def create(
        cls,
        provider: str,
        config: BaseLLMConfig | dict[str, Any],
    ) -> LLMProvider:
        if provider not in cls._registry:
            raise ValueError(
                f"Unsupported LLM provider: {provider!r}. Supported: {sorted(cls._registry)}"
            )

        class_path, config_class = cls._registry[provider]

        if isinstance(config, dict):
            typed_config: BaseLLMConfig = config_class(**config)
        elif isinstance(config, config_class):
            typed_config = config
        elif isinstance(config, BaseLLMConfig):
            # Cross-cast: take only the base fields and let the
            # provider-specific config fill its own defaults.
            base_fields = config.model_dump(include=set(BaseLLMConfig.model_fields))
            typed_config = config_class(**base_fields)
        else:
            raise TypeError(
                f"config must be {config_class.__name__} or dict, got {type(config).__name__}"
            )

        provider_cls = _load_class(class_path)
        return provider_cls(typed_config)

    @classmethod
    def register(
        cls,
        name: str,
        class_path: str,
        config_class: type[BaseLLMConfig],
    ) -> None:
        cls._registry[name] = (class_path, config_class)

    @classmethod
    def unregister(cls, name: str) -> None:
        cls._registry.pop(name, None)

    @classmethod
    def supported_providers(cls) -> list[str]:
        return sorted(cls._registry.keys())

    @classmethod
    def config_class(cls, provider: str) -> type[BaseLLMConfig]:
        if provider not in cls._registry:
            raise ValueError(f"Unsupported LLM provider: {provider!r}")
        return cls._registry[provider][1]
