import type { Brand } from "@/shared/types/brand";
import type { WorkspaceId } from "@/entities/workspace";

export type AgentId = Brand<string, "AgentId">;

export type AgentStatus = "draft" | "active" | "archived";

/** Light shape from list endpoint — no JSONB configs. */
export type AgentSummary = {
  id: AgentId;
  name: string;
  description?: string;
  createdAt: string;
  createdBy?: string;
};

/** Per-agent BYOK override (CreateAgentRequest.provider_credentials). */
export type ProviderCredentialsInput = {
  apiKey: string;
  baseUrl?: string;
  organization?: string;
};

/** Full configuration returned by GET /workspaces/{ws}/agents/{id}. */
export type AgentDetail = {
  id: AgentId;
  workspaceId: WorkspaceId;
  name: string;
  slug: string;
  description?: string;
  role: string;
  systemPrompt: string;
  status: AgentStatus;
  modelProvider: string;
  modelName: string;
  temperature: number;
  maxTokens?: number;
  topP?: number;
  memoryConfig: Record<string, unknown>;
  scheduleConfig: Record<string, unknown>;
  guardrailsConfig: Record<string, unknown>;
  interactionRules: Record<string, unknown>;
  limitsConfig: Record<string, unknown>;
  skillsConfig: Record<string, unknown>;
  /** Spec exposes only a bool — actual key is never returned. */
  providerCredentialsConfigured?: boolean;
  createdBy?: string;
  createdAt: string;
  updatedAt: string;
};

/** Form payload mirroring CreateAgentRequest in the spec. */
export type CreateAgentInput = {
  name: string;
  role: string;
  systemPrompt: string;
  modelProvider: string;
  modelName: string;
  description?: string;
  temperature?: number;
  maxTokens?: number;
  topP?: number;
  /** Optional per-agent BYOK override; sent inline in CreateAgentRequest. */
  providerCredentials?: ProviderCredentialsInput;
  /**
   * Tool slugs to attach. The service serialises these into
   * `skills_config.tools = [{ name, options }]` per `ToolEntryShape`.
   */
  toolSlugs?: string[];
  // ── JSONB runtime configs (opaque to the server, agent-scoped behaviour) ──
  // Each block is sent as-is. The runtime reads well-known keys —
  // `guardrails_config.max_tool_hops`, `limits_config.max_input_tokens`,
  // etc. — but unknown keys are preserved so callers can iterate without
  // a schema change.
  memoryConfig?: Record<string, unknown>;
  scheduleConfig?: Record<string, unknown>;
  guardrailsConfig?: Record<string, unknown>;
  interactionRules?: Record<string, unknown>;
  limitsConfig?: Record<string, unknown>;
};

/** Partial-update payload — every field optional. */
export type UpdateAgentInput = Partial<CreateAgentInput>;

/* ─── Capabilities (GET /api/v1/agents/capabilities) ───────────── */

export type ModelCatalogEntry = {
  name: string;
  displayName: string;
  contextWindow: number;
  supportsTools: boolean;
  supportsStreaming: boolean;
  isDefault: boolean;
};

export type ProviderConfigField = {
  key: string;
  type: string; // "float" | "int" | "string" | "dict"
  required: boolean;
  min?: number;
  max?: number;
  default?: unknown;
  description: string;
};

export type ProviderCapability = {
  key: string;
  displayName: string;
  isConfigured: boolean;
  defaultModel?: string;
  models: ModelCatalogEntry[];
  configFields: ProviderConfigField[];
};

export type FieldSpec = {
  key: string;
  type: string;
  required: boolean;
  minLength?: number;
  maxLength?: number;
  min?: number;
  max?: number;
  default?: unknown;
  description: string;
};

export type ToolCapability = {
  name: string;
  description: string;
  parametersSchema?: Record<string, unknown>;
};

export type ToolEntryShape = {
  nameField: string;
  optionsField: string;
  jsonSchemaExtra?: Record<string, unknown>;
};

/** Spec: schema for the optional per-agent BYOK form field. */
export type ProviderCredentialsShape = {
  fields: FieldSpec[];
  whenRequired?: string;
  storageNote?: string;
};

export type AgentCapabilities = {
  providers: ProviderCapability[];
  fields: { mandatory: FieldSpec[]; optional: FieldSpec[] };
  tools: ToolCapability[];
  toolEntryShape?: ToolEntryShape;
  providerCredentialsShape?: ProviderCredentialsShape;
};
