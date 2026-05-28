"""Server-level agent-creation capabilities.

Exposes everything the agent-builder UI needs to populate dropdowns +
form constraints, without the FE hard-coding any of it:

- Which LLM providers are supported (and which are actually configured)
- Recommended models per provider, with their context window + tool
  support, so the model picker is more than a string field
- Which CreateAgentRequest fields are mandatory vs optional, with bounds
- The expected shape of a tool attachment entry on an agent

The model catalog below is curated, not fetched from each provider's
"list models" API — provider APIs return hundreds of internal variants
(snapshots, dated releases, fine-tunes). The curated short-list is what
we *recommend* and *support tool-calling on*. Add to the dict to expose
more models; this is the only place the UI's model list comes from.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.llm.factory import LLMFactory

# ──────────────────────────────────────────────────────────────────────
# Curated model catalog
# ──────────────────────────────────────────────────────────────────────


class ModelCatalogEntry(BaseModel):
    name: str = Field(description="Provider-specific model id sent to the API.")
    display_name: str
    context_window: int = Field(description="Max input tokens supported.")
    supports_tools: bool
    supports_streaming: bool
    is_default: bool = False


# Curated catalog. Models below are what each provider currently lists in
# their public docs (as of 2026-05). Deprecated entries (gpt-4-turbo,
# gemini-1.5-*, gemini-2.0-*, mixtral-8x7b) are removed — they either no
# longer route or have free-tier quota=0 on new keys.
#
# `supports_tools` is true only for models documented to support function
# calling. `context_window` is the input token limit per the docs;
# output limits vary and aren't surfaced here.
_MODEL_CATALOG: dict[str, list[ModelCatalogEntry]] = {
    # ── OpenAI ────────────────────────────────────────────────────────
    # GPT-5 family is the current flagship line; GPT-4.1 still serves cost
    # tiers and longer-context needs. o-series models are reasoning-optimised
    # (chain-of-thought baked into the API).
    "openai": [
        ModelCatalogEntry(
            name="gpt-5",
            display_name="GPT-5",
            context_window=400_000,
            supports_tools=True,
            supports_streaming=True,
            is_default=True,
        ),
        ModelCatalogEntry(
            name="gpt-5-mini",
            display_name="GPT-5 mini",
            context_window=400_000,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="gpt-5-nano",
            display_name="GPT-5 nano",
            context_window=400_000,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="gpt-4.1",
            display_name="GPT-4.1",
            context_window=1_047_576,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="gpt-4.1-mini",
            display_name="GPT-4.1 mini",
            context_window=1_047_576,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="gpt-4.1-nano",
            display_name="GPT-4.1 nano",
            context_window=1_047_576,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="gpt-4o",
            display_name="GPT-4o",
            context_window=128_000,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="gpt-4o-mini",
            display_name="GPT-4o mini",
            context_window=128_000,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="o3",
            display_name="o3 (reasoning)",
            context_window=200_000,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="o3-mini",
            display_name="o3-mini (reasoning)",
            context_window=200_000,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="o4-mini",
            display_name="o4-mini (reasoning)",
            context_window=200_000,
            supports_tools=True,
            supports_streaming=True,
        ),
    ],
    # ── Google Gemini ─────────────────────────────────────────────────
    # 2.5 family replaces the deprecated 2.0/1.5 lines. Free-tier eligible
    # on AI Studio keys; rate limits differ by sub-model.
    "gemini": [
        ModelCatalogEntry(
            name="gemini-2.5-flash",
            display_name="Gemini 2.5 Flash",
            context_window=1_048_576,
            supports_tools=True,
            supports_streaming=True,
            is_default=True,
        ),
        ModelCatalogEntry(
            name="gemini-2.5-flash-lite",
            display_name="Gemini 2.5 Flash Lite",
            context_window=1_048_576,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="gemini-2.5-pro",
            display_name="Gemini 2.5 Pro",
            context_window=2_097_152,
            supports_tools=True,
            supports_streaming=True,
        ),
    ],
    # ── Groq ──────────────────────────────────────────────────────────
    # Groq hosts open weights at fast inference speeds. Llama 4 + Llama 3.3
    # are current; mixtral-8x7b and llama-3.1-70b were deprecated.
    "groq": [
        ModelCatalogEntry(
            name="llama-3.3-70b-versatile",
            display_name="Llama 3.3 70B (Versatile)",
            context_window=131_072,
            supports_tools=True,
            supports_streaming=True,
            is_default=True,
        ),
        ModelCatalogEntry(
            name="llama-3.1-8b-instant",
            display_name="Llama 3.1 8B (Instant)",
            context_window=131_072,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="meta-llama/llama-4-scout-17b-16e-instruct",
            display_name="Llama 4 Scout 17B",
            context_window=131_072,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="meta-llama/llama-4-maverick-17b-128e-instruct",
            display_name="Llama 4 Maverick 17B",
            context_window=131_072,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="openai/gpt-oss-120b",
            display_name="GPT-OSS 120B",
            context_window=131_072,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="openai/gpt-oss-20b",
            display_name="GPT-OSS 20B",
            context_window=131_072,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="deepseek-r1-distill-llama-70b",
            display_name="DeepSeek R1 Distill Llama 70B",
            context_window=131_072,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="qwen/qwen3-32b",
            display_name="Qwen3 32B",
            context_window=131_072,
            supports_tools=True,
            supports_streaming=True,
        ),
    ],
    # ── OpenRouter ────────────────────────────────────────────────────
    # OpenRouter proxies many providers behind one key. `openrouter/auto`
    # picks per request; `openrouter/free` restricts to free models only.
    # Specific models can be referenced by their canonical OpenRouter id —
    # this is a curated short-list, not exhaustive (the catalog is huge).
    "openrouter": [
        ModelCatalogEntry(
            name="openrouter/auto",
            display_name="OpenRouter Auto",
            context_window=200_000,
            supports_tools=True,
            supports_streaming=True,
            is_default=True,
        ),
        ModelCatalogEntry(
            name="openrouter/free",
            display_name="OpenRouter Free (auto)",
            context_window=131_072,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="anthropic/claude-3.5-sonnet",
            display_name="Claude 3.5 Sonnet",
            context_window=200_000,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="anthropic/claude-3.7-sonnet",
            display_name="Claude 3.7 Sonnet",
            context_window=200_000,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="openai/gpt-4o-mini",
            display_name="GPT-4o mini (via OpenRouter)",
            context_window=128_000,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="google/gemini-2.5-flash",
            display_name="Gemini 2.5 Flash (via OpenRouter)",
            context_window=1_048_576,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="meta-llama/llama-3.3-70b-instruct",
            display_name="Llama 3.3 70B Instruct (via OpenRouter)",
            context_window=131_072,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="deepseek/deepseek-chat-v3-0324",
            display_name="DeepSeek Chat V3",
            context_window=131_072,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="qwen/qwen-2.5-72b-instruct",
            display_name="Qwen 2.5 72B Instruct (via OpenRouter)",
            context_window=131_072,
            supports_tools=True,
            supports_streaming=True,
        ),
        ModelCatalogEntry(
            name="mistralai/mistral-large-2411",
            display_name="Mistral Large (Nov 2024)",
            context_window=131_072,
            supports_tools=True,
            supports_streaming=True,
        ),
    ],
}


_PROVIDER_DISPLAY: dict[str, str] = {
    "openai": "OpenAI",
    "gemini": "Google Gemini",
    "groq": "Groq",
    "openrouter": "OpenRouter",
}


def _has_global_key(_key: str) -> bool:
    # Always False under strict per-agent BYOK — no env-level keys exist.
    # Keeping the function as a stable seam so the capabilities builder
    # below (and the FE form that uses `is_configured`) doesn't change.
    return False


# ──────────────────────────────────────────────────────────────────────
# Response schemas
# ──────────────────────────────────────────────────────────────────────


class ProviderConfigField(BaseModel):
    """A single tunable field on an agent's LLM config."""

    key: str
    type: str = Field(description="`float` | `int` | `string` | `dict`.")
    required: bool
    min: float | int | None = None
    max: float | int | None = None
    default: Any | None = None
    description: str


class ProviderCapability(BaseModel):
    key: str = Field(description="Use this as `model_provider` when creating an agent.")
    display_name: str
    is_configured: bool = Field(
        description="True iff the server has an API key for this provider. "
        "Agents using a non-configured provider cannot be executed."
    )
    default_model: str | None = Field(
        default=None,
        description="The model_name we recommend by default. Null if no models are catalogued.",
    )
    models: list[ModelCatalogEntry]
    config_fields: list[ProviderConfigField] = Field(
        description="Per-agent LLM config knobs (temperature, max_tokens, top_p) with bounds."
    )


class FieldSpec(BaseModel):
    """One CreateAgentRequest field, in a UI-friendly form."""

    key: str
    type: str
    required: bool
    min_length: int | None = None
    max_length: int | None = None
    min: float | int | None = None
    max: float | int | None = None
    default: Any | None = None
    description: str


class AgentFieldCatalog(BaseModel):
    mandatory: list[FieldSpec]
    optional: list[FieldSpec]


class ToolEntryShape(BaseModel):
    """The shape of each entry inside ``agent.skills_config["tools"]``.

    When attaching a tool to an agent, append one of these objects to
    the tools array. ``name`` must match a tool from ``tools[].name``.
    ``options`` is freeform — tool-specific overrides (rate limits, API
    creds, prompt fragments) interpreted by the tool's executor.
    """

    name_field: str = "name"
    options_field: str = "options"
    json_schema_extra: dict[str, Any] = Field(
        default_factory=lambda: {
            "examples": [
                {"name": "calculator", "options": {}},
                {"name": "web_search", "options": {"max_results": 5}},
            ]
        }
    )


class ToolCapability(BaseModel):
    """One built-in tool offered to agents.

    `parameters_schema` is JSON Schema for the tool's input — the LLM
    sees this when deciding whether to call the tool.
    """

    name: str
    description: str
    parameters_schema: dict[str, Any] = Field(default_factory=dict)


class ProviderCredentialsShape(BaseModel):
    """Schema reference for the agent's per-agent `provider_credentials` form field.

    BYOK (bring-your-own-key) lets each agent carry its own provider creds
    that override the server-level key at run time. **Required** when the
    chosen `model_provider` shows `is_configured: false` (server has no
    global key for it).
    """

    fields: list[FieldSpec]
    when_required: str = (
        "When the chosen `model_provider` has `is_configured: false`, the agent "
        "must include `provider_credentials.api_key`. Otherwise it's optional and "
        "overrides the server-level key for this agent's runs only."
    )
    storage_note: str = (
        "Stored as JSONB in Postgres. Never returned in GET responses — only a "
        "`provider_credentials_configured: bool` flag is exposed. Redacted in HTTP access logs."
    )


class AgentCapabilities(BaseModel):
    """Everything needed to render the agent-creation form."""

    providers: list[ProviderCapability]
    fields: AgentFieldCatalog
    tools: list[ToolCapability] = Field(
        default_factory=list,
        description=(
            "Built-in tools available to attach to agents. May be empty in v1 "
            "until the tool registry is wired."
        ),
    )
    tool_entry_shape: ToolEntryShape = Field(
        default_factory=ToolEntryShape,
        description="Shape of each entry to add when attaching tools on an agent's skills_config.",
    )
    provider_credentials_shape: ProviderCredentialsShape = Field(
        description="Schema for the optional `provider_credentials` form field on create."
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "providers": [
                        {
                            "key": "openai",
                            "display_name": "OpenAI",
                            "is_configured": True,
                            "default_model": "gpt-4o-mini",
                            "models": [
                                {
                                    "name": "gpt-4o-mini",
                                    "display_name": "GPT-4o mini",
                                    "context_window": 128000,
                                    "supports_tools": True,
                                    "supports_streaming": True,
                                    "is_default": True,
                                }
                            ],
                            "config_fields": [
                                {
                                    "key": "temperature",
                                    "type": "float",
                                    "required": False,
                                    "min": 0.0,
                                    "max": 2.0,
                                    "default": 0.7,
                                    "description": "Sampling temperature.",
                                }
                            ],
                        }
                    ],
                    "fields": {
                        "mandatory": [
                            {
                                "key": "name",
                                "type": "string",
                                "required": True,
                                "min_length": 1,
                                "max_length": 255,
                                "description": "Display name.",
                            }
                        ],
                        "optional": [],
                    },
                    "tools": [],
                    "tool_entry_shape": {
                        "name_field": "name",
                        "options_field": "options",
                    },
                }
            ]
        }
    )


# ──────────────────────────────────────────────────────────────────────
# Builder
# ──────────────────────────────────────────────────────────────────────


_CONFIG_FIELDS: list[ProviderConfigField] = [
    ProviderConfigField(
        key="temperature",
        type="float",
        required=False,
        min=0.0,
        max=2.0,
        default=0.7,
        description="Sampling temperature. Higher = more creative, lower = more deterministic.",
    ),
    ProviderConfigField(
        key="max_tokens",
        type="int",
        required=False,
        min=1,
        max=128_000,
        default=None,
        description="Cap on output tokens. Null = provider default.",
    ),
    ProviderConfigField(
        key="top_p",
        type="float",
        required=False,
        min=0.0,
        max=1.0,
        default=None,
        description="Nucleus sampling. Mutually-exclusive with temperature in many providers.",
    ),
]


_MANDATORY_FIELDS: list[FieldSpec] = [
    FieldSpec(
        key="name",
        type="string",
        required=True,
        min_length=1,
        max_length=255,
        description="Display name shown in the workflow builder.",
    ),
    FieldSpec(
        key="role",
        type="string",
        required=True,
        min_length=1,
        max_length=120,
        description="Short role label (e.g. `router`, `researcher`).",
    ),
    FieldSpec(
        key="system_prompt",
        type="string",
        required=True,
        min_length=1,
        description="System prompt the LLM receives. Becomes `prompt=` in `create_react_agent`.",
    ),
    FieldSpec(
        key="model_provider",
        type="string",
        required=True,
        description="LLM provider key. Must match one of `providers[].key` with `is_configured = true`.",
    ),
    FieldSpec(
        key="model_name",
        type="string",
        required=True,
        description="Provider-specific model id. Should be one of the catalogued models for the chosen provider.",
    ),
]


_OPTIONAL_FIELDS: list[FieldSpec] = [
    FieldSpec(
        key="description",
        type="string",
        required=False,
        max_length=2000,
        description="Free-text description shown in the picker.",
    ),
    FieldSpec(
        key="temperature",
        type="float",
        required=False,
        min=0.0,
        max=2.0,
        default=0.7,
        description="Sampling temperature.",
    ),
    FieldSpec(
        key="max_tokens",
        type="int",
        required=False,
        min=1,
        max=128_000,
        description="Cap on output tokens. Null = provider default.",
    ),
    FieldSpec(
        key="top_p",
        type="float",
        required=False,
        min=0.0,
        max=1.0,
        description="Nucleus sampling.",
    ),
    FieldSpec(
        key="memory_config",
        type="dict",
        required=False,
        default={},
        description="Memory configuration JSON. Shape is owned by the memory module.",
    ),
    FieldSpec(
        key="schedule_config",
        type="dict",
        required=False,
        default={},
        description="Optional cron-like schedule for autonomous agent runs.",
    ),
    FieldSpec(
        key="guardrails_config",
        type="dict",
        required=False,
        default={},
        description="Input + output filters / safety policies.",
    ),
    FieldSpec(
        key="interaction_rules",
        type="dict",
        required=False,
        default={},
        description="How this agent talks to other agents (routing hints, escalation policy).",
    ),
    FieldSpec(
        key="limits_config",
        type="dict",
        required=False,
        default={},
        description="Per-agent run limits (token cap, max tool hops, wall-clock).",
    ),
    FieldSpec(
        key="skills_config",
        type="dict",
        required=False,
        default={},
        description="Skills / tool attachments. Use `tool_entry_shape` for each tool entry.",
    ),
    FieldSpec(
        key="provider_credentials",
        type="dict",
        required=False,
        default=None,
        description=(
            "Optional per-agent LLM credentials (BYOK). Required when the chosen "
            "`model_provider` has `is_configured: false`. See `provider_credentials_shape`."
        ),
    ),
]


_PROVIDER_CREDENTIALS_FIELDS: list[FieldSpec] = [
    FieldSpec(
        key="api_key",
        type="string",
        required=True,
        min_length=1,
        description="Provider API key (e.g. `sk-...`, `gsk_...`, `AIza...`).",
    ),
    FieldSpec(
        key="base_url",
        type="string",
        required=False,
        description="Custom API base URL. Useful for proxies / OpenAI-compatible endpoints.",
    ),
    FieldSpec(
        key="organization",
        type="string",
        required=False,
        description="OpenAI organization id, if applicable.",
    ),
]


def build_capabilities(
    *,
    user_provider_keys: set[str] | None = None,
    workspace_provider_keys: set[str] | None = None,
) -> AgentCapabilities:
    """Build the capabilities response.

    A provider is marked ``is_configured: true`` if ANY of:
      * the server has a global key (always False under strict BYOK)
      * the user has a vault key for it
      * the **workspace** has a default credential for it

    The workspace-scoped capabilities endpoint passes
    ``workspace_provider_keys`` so the agent-create form can pre-select
    a saved workspace default. The legacy global endpoint passes only
    ``user_provider_keys`` (kept for backwards compat).

    Pure-ish: no DB/network IO here. Reads the curated catalogs above.
    """

    user_keys = user_provider_keys or set()
    ws_keys = workspace_provider_keys or set()
    supported = set(LLMFactory.supported_providers())
    providers: list[ProviderCapability] = []
    for key in sorted(supported):
        models = _MODEL_CATALOG.get(key, [])
        default = next((m.name for m in models if m.is_default), None) or (
            models[0].name if models else None
        )
        is_configured = _has_global_key(key) or key in user_keys or key in ws_keys
        providers.append(
            ProviderCapability(
                key=key,
                display_name=_PROVIDER_DISPLAY.get(key, key.capitalize()),
                is_configured=is_configured,
                default_model=default,
                models=models,
                config_fields=_CONFIG_FIELDS,
            )
        )

    return AgentCapabilities(
        providers=providers,
        fields=AgentFieldCatalog(
            mandatory=_MANDATORY_FIELDS,
            optional=_OPTIONAL_FIELDS,
        ),
        tools=[],  # populated when the tool registry is wired
        provider_credentials_shape=ProviderCredentialsShape(
            fields=_PROVIDER_CREDENTIALS_FIELDS,
        ),
    )
