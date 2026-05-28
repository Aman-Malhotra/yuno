"""Legacy compatibility stub.

Previously this module pre-built one shared provider per LLM service from
env-level keys. Under the strict per-agent BYOK model, providers are
instantiated *per agent* by ``runtime/nodes.py:run_agent`` using the
agent row's own ``provider_credentials.api_key``. There is no longer a
single shared registry to seed at startup.

Kept as an empty entry point in case any caller still imports it; remove
once the call sites disappear.
"""

from app.modules.llm.providers.base import LLMProvider


def build_llm_registry() -> dict[str, LLMProvider]:
    return {}
