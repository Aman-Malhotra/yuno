from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agent Orchestrator"
    environment: str = "local"

    # Required — no defaults. Set in .env (gitignored) and via the
    # docker-compose `environment:` block for container runs.
    database_url: str
    redis_url: str
    jwt_secret_key: str = Field(
        min_length=32,
        description="HMAC signing key. Must be ≥32 bytes for HS256.",
    )

    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 12 * 60  # 12 hours
    refresh_token_expire_days: int = 30

    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    # ── HTTP access logging ────────────────────────────────────────────
    log_http_bodies: bool = Field(
        default=False,
        description="When true, the access log includes request+response bodies (truncated). Dev only.",
    )
    log_max_body_bytes: int = Field(
        default=4096,
        description="Per-side cap for logged bodies; longer payloads are truncated with a marker.",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, value: str | list[str] | None) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value

    # ── NOTE on credentials ──────────────────────────────────────────
    # No LLM or 3rd-party API keys live in env. They are scoped strictly:
    #   * LLM key   → `agents.provider_credentials.api_key` (per agent)
    #   * Tool key  → `tools.auth_config.*` (per tool)
    # A step fails immediately if its row is missing a key; there is no
    # workspace vault, no user vault, no env fallback. Keep the secret
    # close to the thing that uses it.
    #
    # The two env values below are *not* credentials — they're our own
    # ingress-side auth/binding for inbound Telegram webhooks.
    telegram_webhook_secret: str | None = None
    telegram_workflow_id: str | None = None
    telegram_workspace_id: str | None = None

    # ── Memory (mem0 + pgvector + Neo4j) ──────────────────────────────
    # Long-term memory is *infrastructure*, not per-agent: one shared
    # key powers all extractions across the workspace.
    #
    # We route through OpenRouter using mem0's `openai` provider with a
    # custom base_url. OpenRouter exposes hundreds of models under one
    # OpenAI-compatible endpoint, including free-tier models suitable
    # for fact extraction. mem0 doesn't ship a native `openrouter`
    # provider, so the openai-compatible path is the canonical workaround.
    openrouter_api_key_memory: str | None = Field(
        default=None,
        description="OpenRouter API key used by mem0 for fact extraction. "
        "Required when any agent's `memory_config.enable_long_term` is true.",
    )
    mem0_llm_model: str = Field(
        default="openai/gpt-4o-mini",
        description="OpenRouter model id (e.g. `openai/gpt-4o-mini`, "
        "`openrouter/auto`, `meta-llama/llama-3.3-70b-instruct`).",
    )
    mem0_openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
    )
    # Groq doesn't offer embeddings. Default to a local sentence-transformers
    # model so memory works without a 2nd paid API. Swap via env if you'd
    # rather pay OpenAI for higher-quality embeddings.
    mem0_embedder_provider: str = Field(default="huggingface")
    mem0_embedder_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    mem0_embedder_api_key: str | None = Field(
        default=None,
        description="Only required when mem0_embedder_provider is `openai`.",
    )

    # Neo4j (graph memory). Bolt URL is what mem0 wants.
    neo4j_url: str = Field(default="bolt://neo4j:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="agentpass")

    # Defaults applied when an agent doesn't override via memory_config.
    memory_default_history_turns: int = Field(
        default=10,
        ge=0,
        le=100,
        description="How many recent agent_messages to replay before the LLM call.",
    )
    memory_default_recall_k: int = Field(
        default=5,
        ge=0,
        le=50,
        description="How many long-term mem0 memories to inject as context.",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
