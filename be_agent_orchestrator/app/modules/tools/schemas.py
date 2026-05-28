"""Pydantic request/response shapes for the tool registry."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ──────────────────────────────────────────────────────────────────────
# Vocab
# ──────────────────────────────────────────────────────────────────────

ToolType = Literal[
    "builtin",
    "http",
    "messaging",
    "agent_handoff",
    "webhook",
    "python",
    "mock",
]
ToolStatus = Literal["draft", "active", "disabled", "archived"]
AuthType = Literal["none", "bearer", "api_key", "basic", "custom_header"]
ExecutionStatus = Literal[
    "queued",
    "running",
    "success",
    "completed",
    "failed",
    "timeout",
    "cancelled",
    "pending_approval",
]
ApprovalStatus = Literal["pending", "approved", "rejected", "expired"]
LogLevel = Literal["debug", "info", "warn", "error"]


# ──────────────────────────────────────────────────────────────────────
# Inner configs — every tool stores its per-type config under `config`
# ──────────────────────────────────────────────────────────────────────


class KeyValue(BaseModel):
    key: str
    value: str

    model_config = ConfigDict(extra="forbid")


class HttpToolConfig(BaseModel):
    """Config used by the HTTP tool executor.

    The body can be:
    - omitted (GET-style)
    - a JSON object (sent as JSON)
    - a string template (sent as text/form depending on `content_type`)

    All values support `{{input.x}}`, `{{secrets.x}}`, `{{agent.id}}`,
    `{{workflow.run_id}}` placeholders, resolved by the executor at
    dispatch time.
    """

    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET"
    url: str = Field(
        min_length=1, description="Templated URL. e.g. `https://api.x/users/{{input.id}}`."
    )
    headers: list[KeyValue] = Field(default_factory=list)
    query_params: list[KeyValue] = Field(default_factory=list)
    body_template: Any | None = Field(
        default=None,
        description="JSON object or string. Placeholders supported.",
    )
    content_type: str = Field(default="application/json")
    timeout_ms: int = Field(default=10_000, ge=100, le=120_000)

    model_config = ConfigDict(extra="forbid")


class MessagingToolConfig(BaseModel):
    provider: Literal["slack", "telegram", "whatsapp"]
    channel_connection_id: UUID | None = Field(
        default=None,
        description="Optional default channel connection. Inputs can override.",
    )
    default_channel: str | None = None

    model_config = ConfigDict(extra="forbid")


class AgentHandoffToolConfig(BaseModel):
    """Lets one agent call another agent as a tool."""

    target_agent_id: UUID | None = Field(
        default=None,
        description=("Pinned target. If null, the LLM picks via `target_agent_id` in the input."),
    )
    wait_for_response: bool = Field(default=True)
    timeout_ms: int = Field(default=60_000, ge=500, le=600_000)

    model_config = ConfigDict(extra="forbid")


class WebhookToolConfig(BaseModel):
    url: str = Field(min_length=1)
    headers: list[KeyValue] = Field(default_factory=list)
    body_template: Any | None = None
    timeout_ms: int = Field(default=5_000, ge=100, le=60_000)

    model_config = ConfigDict(extra="forbid")


class BuiltinToolConfig(BaseModel):
    """Picks a registered handler from ``app.modules.tools.builtins``."""

    handler: str = Field(min_length=1, description="Registered handler key (e.g. `web_search`).")
    options: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


# ──────────────────────────────────────────────────────────────────────
# Auth + Guardrails + Policy
# ──────────────────────────────────────────────────────────────────────


class AuthConfig(BaseModel):
    type: AuthType = "none"
    # References to secret rows: {"slack_bot_token": "secret_id"}
    secret_refs: dict[str, str] = Field(default_factory=dict)
    # For api_key: which header name to use.
    header_name: str | None = None

    # Inline per-tool BYOK: each builtin reads its own well-known key here
    # (`api_key`, `bot_token`, etc.) via ``BuiltinContext.auth``. Allowed as
    # opaque extras so we don't have to grow this schema every time a new
    # builtin lands. Strict scope: no env fallback — if it's empty, the
    # step fails. Treat the contents like a secret in logs.
    model_config = ConfigDict(extra="allow")


class GuardrailsConfig(BaseModel):
    requires_human_approval: bool = False
    confirmation_message: str | None = None
    allowed_domains: list[str] = Field(default_factory=list)
    blocked_domains: list[str] = Field(default_factory=list)
    rate_limit_per_minute: int | None = Field(default=None, ge=1)
    allow_destructive_action: bool = False

    model_config = ConfigDict(extra="forbid")


class ExecutionPolicy(BaseModel):
    timeout_ms: int = Field(default=10_000, ge=100, le=600_000)
    retry_count: int = Field(default=0, ge=0, le=5)
    retry_backoff_ms: int = Field(default=500, ge=0, le=60_000)
    continue_on_failure: bool = False
    fallback_tool_id: UUID | None = None

    model_config = ConfigDict(extra="forbid")


class ChannelConfig(BaseModel):
    web: bool = True
    slack: bool = True
    telegram: bool = True
    workflow_only: bool = False

    model_config = ConfigDict(extra="forbid")


# ──────────────────────────────────────────────────────────────────────
# JSON Schema field for input/output — kept opaque (Draft-07 JSON Schema)
# ──────────────────────────────────────────────────────────────────────


JsonSchemaDict = dict[str, Any]


# ──────────────────────────────────────────────────────────────────────
# Requests
# ──────────────────────────────────────────────────────────────────────


_DEFAULT_INPUT_SCHEMA: JsonSchemaDict = {
    "type": "object",
    "properties": {},
    "required": [],
}
_DEFAULT_OUTPUT_SCHEMA: JsonSchemaDict = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "data": {"type": "object"},
        "error": {"type": "string"},
    },
}


class CreateToolRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(
        min_length=1,
        description=(
            "Free-text, but treat this as the LLM-facing tool docstring — the "
            "model uses it to decide when to call the tool. Be specific."
        ),
    )
    type: ToolType
    category: str = Field(default="general", max_length=64)
    icon: str | None = Field(default=None, max_length=120)

    input_schema: JsonSchemaDict = Field(
        default_factory=lambda: dict(_DEFAULT_INPUT_SCHEMA),
        description="Draft-07 JSON Schema describing the input arguments.",
    )
    output_schema: JsonSchemaDict = Field(
        default_factory=lambda: dict(_DEFAULT_OUTPUT_SCHEMA),
        description="Draft-07 JSON Schema describing the tool's return shape.",
    )

    config: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Per-type executor config. Shape matches one of "
            "`HttpToolConfig`, `MessagingToolConfig`, `AgentHandoffToolConfig`, "
            "`WebhookToolConfig`, `BuiltinToolConfig` depending on `type`."
        ),
    )
    auth: AuthConfig = Field(default_factory=AuthConfig)
    guardrails: GuardrailsConfig = Field(default_factory=GuardrailsConfig)
    execution_policy: ExecutionPolicy = Field(default_factory=ExecutionPolicy)
    channels: ChannelConfig = Field(default_factory=ChannelConfig)

    status: ToolStatus = Field(default="draft")

    @field_validator("name")
    @classmethod
    def _strip(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Send Slack message",
                    "description": (
                        "Send a message to a Slack channel. Use whenever a "
                        "human needs to be notified or a result needs to be shared."
                    ),
                    "type": "messaging",
                    "category": "communication",
                    "icon": "slack",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "channel": {"type": "string", "description": "Slack channel ID."},
                            "message": {"type": "string"},
                        },
                        "required": ["channel", "message"],
                    },
                    "config": {"provider": "slack"},
                    "auth": {"type": "bearer", "secret_refs": {"token": "slack_bot_token"}},
                    "guardrails": {"requires_human_approval": False},
                    "execution_policy": {"timeout_ms": 5000, "retry_count": 1},
                }
            ]
        }
    )


class UpdateToolRequest(BaseModel):
    """Partial update — every field optional. Omit to leave unchanged."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    category: str | None = Field(default=None, max_length=64)
    icon: str | None = Field(default=None, max_length=120)

    input_schema: JsonSchemaDict | None = None
    output_schema: JsonSchemaDict | None = None
    config: dict[str, Any] | None = None
    auth: AuthConfig | None = None
    guardrails: GuardrailsConfig | None = None
    execution_policy: ExecutionPolicy | None = None
    channels: ChannelConfig | None = None
    status: ToolStatus | None = None

    publish_new_version: bool = Field(
        default=False,
        description=(
            "If true, snapshot the updated tool to a new `tool_versions` row "
            "before saving. Workflow runs pinned to older versions keep "
            "executing the original behaviour."
        ),
    )

    model_config = ConfigDict(extra="forbid")


# ──────────────────────────────────────────────────────────────────────
# Responses
# ──────────────────────────────────────────────────────────────────────


class ToolSummary(BaseModel):
    """Light shape for the list endpoint."""

    id: UUID
    name: str
    slug: str
    description: str
    type: ToolType
    category: str
    icon: str | None = None
    status: ToolStatus
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ToolDetail(BaseModel):
    """Full tool definition. Returned by the detail endpoint and after writes."""

    id: UUID
    workspace_id: UUID | None
    name: str
    slug: str
    description: str
    type: ToolType
    category: str
    icon: str | None = None
    status: ToolStatus
    version: int

    input_schema: JsonSchemaDict
    output_schema: JsonSchemaDict
    config: dict[str, Any]
    auth: AuthConfig
    guardrails: GuardrailsConfig
    execution_policy: ExecutionPolicy
    channels: ChannelConfig

    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm(cls, tool: object) -> "ToolDetail":
        return cls(
            id=tool.id,  # type: ignore[attr-defined]
            workspace_id=tool.workspace_id,  # type: ignore[attr-defined]
            name=tool.name,  # type: ignore[attr-defined]
            slug=tool.slug,  # type: ignore[attr-defined]
            description=tool.description,  # type: ignore[attr-defined]
            type=tool.type,  # type: ignore[attr-defined]
            category=tool.category,  # type: ignore[attr-defined]
            icon=tool.icon,  # type: ignore[attr-defined]
            status=tool.status,  # type: ignore[attr-defined]
            version=tool.version,  # type: ignore[attr-defined]
            input_schema=tool.input_schema or dict(_DEFAULT_INPUT_SCHEMA),  # type: ignore[attr-defined]
            output_schema=tool.output_schema or dict(_DEFAULT_OUTPUT_SCHEMA),  # type: ignore[attr-defined]
            config=tool.config or {},  # type: ignore[attr-defined]
            auth=AuthConfig(
                type=(tool.auth_type or "none"),  # type: ignore[attr-defined]
                **(tool.auth_config or {}),  # type: ignore[attr-defined]
            ),
            guardrails=GuardrailsConfig(**(tool.guardrails or {})),  # type: ignore[attr-defined]
            execution_policy=ExecutionPolicy(**(tool.execution_policy or {})),  # type: ignore[attr-defined]
            channels=ChannelConfig(**(tool.channel_config or {})),  # type: ignore[attr-defined]
            created_by=tool.created_by,  # type: ignore[attr-defined]
            created_at=tool.created_at,  # type: ignore[attr-defined]
            updated_at=tool.updated_at,  # type: ignore[attr-defined]
        )


class ToolVersionSummary(BaseModel):
    id: UUID
    tool_id: UUID
    version_number: int
    name: str
    type: ToolType
    created_at: datetime
    created_by: UUID | None

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────
# Execution
# ──────────────────────────────────────────────────────────────────────


class ExecuteToolRequest(BaseModel):
    """Synchronous test invocation from the tool console."""

    input: dict[str, Any] = Field(default_factory=dict)
    agent_id: UUID | None = Field(
        default=None,
        description="Run the tool as if invoked from this agent (uses its permissions/guardrails).",
    )
    dry_run: bool = Field(
        default=False,
        description="When true, render the resolved request payload without dispatching it.",
    )

    model_config = ConfigDict(extra="forbid")


class ToolExecutionLogEntry(BaseModel):
    id: UUID
    level: LogLevel
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ToolExecutionDetail(BaseModel):
    id: UUID
    tool_id: UUID | None
    tool_name: str
    tool_version: int
    agent_id: UUID | None
    run_id: UUID | None
    status: ExecutionStatus

    input: dict[str, Any]
    output: dict[str, Any]

    error_message: str | None = None
    error_details: dict[str, Any] = Field(default_factory=dict)

    duration_ms: int | None = None
    retry_count: int = 0
    tokens_used: int | None = None
    cost_usd: float | None = None

    started_at: datetime
    completed_at: datetime | None = None
    created_at: datetime

    logs: list[ToolExecutionLogEntry] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────
# Approvals
# ──────────────────────────────────────────────────────────────────────


class ApprovalDecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str | None = Field(default=None, max_length=2000)

    model_config = ConfigDict(extra="forbid")


class ToolApprovalDetail(BaseModel):
    id: UUID
    execution_id: UUID
    requested_by_agent_id: UUID | None
    status: ApprovalStatus
    prompt: str | None = None
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────
# Agent ↔ Tool permission
# ──────────────────────────────────────────────────────────────────────


class AgentToolPermissionConfig(BaseModel):
    approval_required: bool = False
    max_calls_per_run: int = Field(default=0, ge=0, description="0 = unlimited.")
    call_rate_per_minute: int | None = Field(default=None, ge=1)
    input_overrides: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class AttachToolRequest(BaseModel):
    tool_id: UUID
    is_enabled: bool = True
    permission: AgentToolPermissionConfig = Field(default_factory=AgentToolPermissionConfig)

    model_config = ConfigDict(extra="forbid")


class AgentToolDetail(BaseModel):
    id: UUID
    agent_id: UUID
    tool_id: UUID
    is_enabled: bool
    permission: AgentToolPermissionConfig
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
