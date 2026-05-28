import { z } from "zod";
import type { AgentCapabilities, AgentDetail, AgentId, AgentSummary } from "./agent.types";
import type { WorkspaceId } from "@/entities/workspace";

const agentIdSchema = z
  .string()
  .min(1)
  .transform((s) => s as AgentId);
const workspaceIdSchema = z
  .string()
  .min(1)
  .transform((s) => s as WorkspaceId);

export const agentStatusSchema = z.enum(["draft", "active", "archived"]);

/* ─── Summary + Detail wire schemas ─────────────────────────────── */

const agentSummaryWireSchema = z.object({
  id: agentIdSchema,
  name: z.string(),
  description: z.string().nullable().optional(),
  created_at: z.string(),
  created_by: z.string().nullable().optional(),
});

export function toAgentSummary(a: z.infer<typeof agentSummaryWireSchema>): AgentSummary {
  return {
    id: a.id,
    name: a.name,
    description: a.description ?? undefined,
    createdAt: a.created_at,
    createdBy: a.created_by ?? undefined,
  };
}

const jsonbSchema = z.record(z.string(), z.unknown());

const agentDetailWireSchema = z.object({
  id: agentIdSchema,
  workspace_id: workspaceIdSchema,
  name: z.string(),
  slug: z.string(),
  description: z.string().nullable().optional(),
  role: z.string(),
  system_prompt: z.string(),
  status: agentStatusSchema,
  model_provider: z.string(),
  model_name: z.string(),
  temperature: z.number(),
  max_tokens: z.number().nullable().optional(),
  top_p: z.number().nullable().optional(),
  memory_config: jsonbSchema.default({}),
  schedule_config: jsonbSchema.default({}),
  guardrails_config: jsonbSchema.default({}),
  interaction_rules: jsonbSchema.default({}),
  limits_config: jsonbSchema.default({}),
  skills_config: jsonbSchema.default({}),
  provider_credentials_configured: z.boolean().optional(),
  created_by: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export function toAgentDetail(a: z.infer<typeof agentDetailWireSchema>): AgentDetail {
  return {
    id: a.id,
    workspaceId: a.workspace_id,
    name: a.name,
    slug: a.slug,
    description: a.description ?? undefined,
    role: a.role,
    systemPrompt: a.system_prompt,
    status: a.status,
    modelProvider: a.model_provider,
    modelName: a.model_name,
    temperature: a.temperature,
    maxTokens: a.max_tokens ?? undefined,
    topP: a.top_p ?? undefined,
    memoryConfig: a.memory_config,
    scheduleConfig: a.schedule_config,
    guardrailsConfig: a.guardrails_config,
    interactionRules: a.interaction_rules,
    limitsConfig: a.limits_config,
    skillsConfig: a.skills_config,
    providerCredentialsConfigured: a.provider_credentials_configured,
    createdBy: a.created_by ?? undefined,
    createdAt: a.created_at,
    updatedAt: a.updated_at,
  };
}

/* ─── Capabilities wire schema (GET /agents/capabilities) ────── */

const modelCatalogEntryWireSchema = z.object({
  name: z.string(),
  display_name: z.string(),
  context_window: z.number(),
  supports_tools: z.boolean(),
  supports_streaming: z.boolean(),
  is_default: z.boolean().default(false),
});

const providerConfigFieldWireSchema = z.object({
  key: z.string(),
  type: z.string(),
  required: z.boolean(),
  min: z.number().nullable().optional(),
  max: z.number().nullable().optional(),
  default: z.unknown().optional(),
  description: z.string(),
});

const providerCapabilityWireSchema = z.object({
  key: z.string(),
  display_name: z.string(),
  is_configured: z.boolean(),
  default_model: z.string().nullable().optional(),
  models: z.array(modelCatalogEntryWireSchema),
  config_fields: z.array(providerConfigFieldWireSchema),
});

const fieldSpecWireSchema = z.object({
  key: z.string(),
  type: z.string(),
  required: z.boolean(),
  min_length: z.number().nullable().optional(),
  max_length: z.number().nullable().optional(),
  min: z.number().nullable().optional(),
  max: z.number().nullable().optional(),
  default: z.unknown().optional(),
  description: z.string(),
});

const toolCapabilityWireSchema = z.object({
  name: z.string(),
  description: z.string(),
  parameters_schema: jsonbSchema.optional(),
});

const toolEntryShapeWireSchema = z.object({
  name_field: z.string().default("name"),
  options_field: z.string().default("options"),
  json_schema_extra: jsonbSchema.optional(),
});

const providerCredentialsShapeWireSchema = z.object({
  fields: z.array(fieldSpecWireSchema),
  when_required: z.string().optional(),
  storage_note: z.string().optional(),
});

const agentCapabilitiesWireSchema = z.object({
  providers: z.array(providerCapabilityWireSchema),
  fields: z.object({
    mandatory: z.array(fieldSpecWireSchema),
    optional: z.array(fieldSpecWireSchema),
  }),
  tools: z.array(toolCapabilityWireSchema).default([]),
  tool_entry_shape: toolEntryShapeWireSchema.optional(),
  provider_credentials_shape: providerCredentialsShapeWireSchema.optional(),
});

function mapField(f: z.infer<typeof fieldSpecWireSchema>) {
  return {
    key: f.key,
    type: f.type,
    required: f.required,
    minLength: f.min_length ?? undefined,
    maxLength: f.max_length ?? undefined,
    min: f.min ?? undefined,
    max: f.max ?? undefined,
    default: f.default,
    description: f.description,
  };
}

export function toAgentCapabilities(c: z.infer<typeof agentCapabilitiesWireSchema>): AgentCapabilities {
  return {
    providers: c.providers.map((p) => ({
      key: p.key,
      displayName: p.display_name,
      isConfigured: p.is_configured,
      defaultModel: p.default_model ?? undefined,
      models: p.models.map((m) => ({
        name: m.name,
        displayName: m.display_name,
        contextWindow: m.context_window,
        supportsTools: m.supports_tools,
        supportsStreaming: m.supports_streaming,
        isDefault: m.is_default,
      })),
      configFields: p.config_fields.map((f) => ({
        key: f.key,
        type: f.type,
        required: f.required,
        min: f.min ?? undefined,
        max: f.max ?? undefined,
        default: f.default,
        description: f.description,
      })),
    })),
    fields: {
      mandatory: c.fields.mandatory.map(mapField),
      optional: c.fields.optional.map(mapField),
    },
    tools: c.tools.map((t) => ({
      name: t.name,
      description: t.description,
      parametersSchema: t.parameters_schema,
    })),
    toolEntryShape: c.tool_entry_shape
      ? {
          nameField: c.tool_entry_shape.name_field,
          optionsField: c.tool_entry_shape.options_field,
          jsonSchemaExtra: c.tool_entry_shape.json_schema_extra,
        }
      : undefined,
    providerCredentialsShape: c.provider_credentials_shape
      ? {
          fields: c.provider_credentials_shape.fields.map(mapField),
          whenRequired: c.provider_credentials_shape.when_required,
          storageNote: c.provider_credentials_shape.storage_note,
        }
      : undefined,
  };
}

export { agentSummaryWireSchema, agentDetailWireSchema, agentCapabilitiesWireSchema };
