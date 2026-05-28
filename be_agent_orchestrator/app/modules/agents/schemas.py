from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

AgentStatus = Literal["draft", "active", "archived"]


# ──────────────────────────────────────────────────────────────────────
# BYOK — per-agent provider credentials
# ──────────────────────────────────────────────────────────────────────


class ProviderCredentialsConfig(BaseModel):
    """Per-agent override of the server-level LLM provider credentials.

    Optional. When set, ``api_key`` overrides ``settings.<provider>_api_key``
    for this agent's runs. ``base_url`` + ``organization`` are honored where
    the provider's SDK supports them (OpenAI; Groq supports `base_url`).

    Security:
    - The api_key is **stored as-is in JSONB** (Postgres TDE only). Treat
      Postgres read access as equivalent to having the key.
    - The api_key is **never returned in any GET response** — only a
      ``provider_credentials_configured: bool`` flag.
    - Whole ``provider_credentials`` subtree is redacted in HTTP access logs.
    """

    api_key: str = Field(
        min_length=1,
        description="Provider API key (e.g. `sk-...`, `gsk_...`, `AIza...`).",
    )
    base_url: str | None = Field(
        default=None,
        description="Custom API base URL. Useful for proxies (OpenAI-compatible endpoints, Groq mirrors).",
    )
    organization: str | None = Field(
        default=None,
        description="OpenAI organization id, if applicable.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"api_key": "sk-proj-..."},
                {"api_key": "gsk_...", "base_url": "https://api.groq.com/openai/v1"},
            ]
        }
    )


# ──────────────────────────────────────────────────────────────────────
# Requests
# ──────────────────────────────────────────────────────────────────────

# Five fields are mandatory because they're the minimum LangGraph needs to
# materialize an agent node at runtime via ``create_react_agent``:
#
#   create_react_agent(
#       model    = ChatXxx(model=<model_name>, ...),   # ← model_provider + model_name
#       tools    = [...],                              # optional (LLM-only agent OK)
#       prompt   = <system_prompt>,                    # ← system_prompt
#   )
#
# ``name`` and ``role`` are mandatory for our own UI/orchestration layer
# (display + the agent's position in the workflow conversation).


class CreateAgentRequest(BaseModel):
    # ── Mandatory ──────────────────────────────────────────────────────
    name: str = Field(
        min_length=1,
        max_length=255,
        description="Human-readable display name shown in the workflow builder.",
    )
    role: str = Field(
        min_length=1,
        max_length=120,
        description="Short role label (e.g. `triage`, `researcher`, `chart_generator`).",
    )
    system_prompt: str = Field(
        min_length=1,
        description="System prompt the LLM receives. Becomes `prompt=` in `create_react_agent`.",
    )
    model_provider: str = Field(
        min_length=1,
        max_length=64,
        description="LLM provider key. Must match a configured provider (`openai`, `gemini`, `groq`).",
    )
    model_name: str = Field(
        min_length=1,
        max_length=120,
        description="Provider-specific model identifier, e.g. `gpt-4o-mini`, `gemini-2.0-flash`, `llama-3.3-70b-versatile`.",
    )

    # ── Optional knobs with sane defaults ──────────────────────────────
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Free-text description shown in the agent picker / hover card.",
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=128_000)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)

    # ── Optional JSONB configs (all default to {}) ─────────────────────
    memory_config: dict[str, Any] = Field(default_factory=dict)
    schedule_config: dict[str, Any] = Field(default_factory=dict)
    guardrails_config: dict[str, Any] = Field(default_factory=dict)
    interaction_rules: dict[str, Any] = Field(default_factory=dict)
    limits_config: dict[str, Any] = Field(default_factory=dict)
    skills_config: dict[str, Any] = Field(default_factory=dict)

    # ── Optional BYOK ────────────────────────────────────────────────────
    provider_credentials: ProviderCredentialsConfig | None = Field(
        default=None,
        description=(
            "Per-agent LLM provider credentials. When omitted, the agent uses "
            "the server-level API key for `model_provider` from `.env`. "
            "**Required** when the provider is not globally configured."
        ),
    )

    @field_validator("name", "role", "system_prompt", "model_provider", "model_name")
    @classmethod
    def _strip_whitespace(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Support Router",
                    "role": "router",
                    "system_prompt": "You are the front-line router for inbound customer messages. "
                    "Classify each message into one of: billing, technical, sales. "
                    "Hand off to the appropriate specialist agent.",
                    "model_provider": "openai",
                    "model_name": "gpt-4o-mini",
                    "description": "Classifies inbound tickets and dispatches to specialists.",
                    "temperature": 0.2,
                }
            ]
        }
    )


# ──────────────────────────────────────────────────────────────────────
# Update — partial; every field optional. Omit to leave unchanged.
# ──────────────────────────────────────────────────────────────────────


class UpdateAgentRequest(BaseModel):
    """Patch shape for the agent editor.

    Every field is optional. `provider_credentials` lets the user rotate
    the BYOK key in place — pass `{"api_key": "..."}` to overwrite the
    stored credential block. Pass an explicit empty object `{}` to clear
    BYOK and fall back to the user vault / global key.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = Field(default=None, min_length=1, max_length=120)
    system_prompt: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, max_length=2000)

    model_provider: str | None = Field(default=None, min_length=1, max_length=64)
    model_name: str | None = Field(default=None, min_length=1, max_length=120)

    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=128_000)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)

    status: AgentStatus | None = None

    memory_config: dict[str, Any] | None = None
    schedule_config: dict[str, Any] | None = None
    guardrails_config: dict[str, Any] | None = None
    interaction_rules: dict[str, Any] | None = None
    limits_config: dict[str, Any] | None = None
    skills_config: dict[str, Any] | None = None

    provider_credentials: ProviderCredentialsConfig | None = None

    model_config = ConfigDict(extra="forbid")


# ──────────────────────────────────────────────────────────────────────
# List shape — what the list endpoint returns per row
# ──────────────────────────────────────────────────────────────────────


class AgentSummary(BaseModel):
    """Light shape for the list endpoint — no JSONB configs (kilobytes+ per row)."""

    id: UUID
    name: str
    description: str | None = None
    created_at: datetime
    created_by: UUID | None = Field(
        default=None,
        description="User who authored the agent. Null if that user was deleted.",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "01HZX9F4Y0N0N5J5R0Q6Z3M8B2",
                    "name": "Support Router",
                    "description": "Classifies inbound questions and hands off to a specialist.",
                    "created_at": "2026-05-23T18:42:13.812000Z",
                    "created_by": "01HZX9F4Y0N0N5J5R0Q6Z3M8AB",
                }
            ]
        },
    )


# ──────────────────────────────────────────────────────────────────────
# Detail shape — everything you need to render the agent editor
# ──────────────────────────────────────────────────────────────────────


class AgentDetail(BaseModel):
    """Full agent configuration. Returned by the detail endpoint.

    The JSONB blobs (memory/schedule/guardrails/interaction_rules/limits/
    skills) are returned as opaque dicts here — frontend renders them via
    the agent-editor module. Backend doesn't impose a schema on these
    fields yet; that comes when we wire the runtime executor.
    """

    id: UUID
    workspace_id: UUID
    name: str
    slug: str
    description: str | None = None

    role: str = Field(description="Short role label, e.g. `triage`, `researcher`.")
    system_prompt: str

    status: AgentStatus

    model_provider: str = Field(description="`openai` | `gemini` | `groq` | …")
    model_name: str
    temperature: float
    max_tokens: int | None = None
    top_p: float | None = None

    memory_config: dict[str, Any] = Field(default_factory=dict)
    schedule_config: dict[str, Any] = Field(default_factory=dict)
    guardrails_config: dict[str, Any] = Field(default_factory=dict)
    interaction_rules: dict[str, Any] = Field(default_factory=dict)
    limits_config: dict[str, Any] = Field(default_factory=dict)
    skills_config: dict[str, Any] = Field(default_factory=dict)

    # BYOK: surface presence, never the key itself.
    provider_credentials_configured: bool = Field(
        default=False,
        description=(
            "True iff the agent carries its own provider credentials. "
            "The actual key is never returned by any endpoint."
        ),
    )

    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_agent(cls, agent: object) -> "AgentDetail":
        """Build from an ORM ``Agent`` row, deriving the credential flag.

        Use this instead of ``model_validate`` so the BYOK key never gets
        anywhere near the response body, even by accident.
        """

        return cls(
            id=agent.id,  # type: ignore[attr-defined]
            workspace_id=agent.workspace_id,  # type: ignore[attr-defined]
            name=agent.name,  # type: ignore[attr-defined]
            slug=agent.slug,  # type: ignore[attr-defined]
            description=agent.description,  # type: ignore[attr-defined]
            role=agent.role,  # type: ignore[attr-defined]
            system_prompt=agent.system_prompt,  # type: ignore[attr-defined]
            status=agent.status,  # type: ignore[attr-defined]
            model_provider=agent.model_provider,  # type: ignore[attr-defined]
            model_name=agent.model_name,  # type: ignore[attr-defined]
            temperature=float(agent.temperature),  # type: ignore[attr-defined]
            max_tokens=agent.max_tokens,  # type: ignore[attr-defined]
            top_p=float(agent.top_p) if agent.top_p is not None else None,  # type: ignore[attr-defined]
            memory_config=agent.memory_config,  # type: ignore[attr-defined]
            schedule_config=agent.schedule_config,  # type: ignore[attr-defined]
            guardrails_config=agent.guardrails_config,  # type: ignore[attr-defined]
            interaction_rules=agent.interaction_rules,  # type: ignore[attr-defined]
            limits_config=agent.limits_config,  # type: ignore[attr-defined]
            skills_config=agent.skills_config,  # type: ignore[attr-defined]
            provider_credentials_configured=bool(
                (agent.provider_credentials or {}).get("api_key")  # type: ignore[attr-defined]
            ),
            created_by=agent.created_by,  # type: ignore[attr-defined]
            created_at=agent.created_at,  # type: ignore[attr-defined]
            updated_at=agent.updated_at,  # type: ignore[attr-defined]
        )
