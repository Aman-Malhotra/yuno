import { z } from "zod";
import type { ToolDetail, ToolId, ToolSummary, ToolVersionSummary } from "./tool.types";
import type { WorkspaceId } from "@/entities/workspace";

const toolIdSchema = z
  .string()
  .min(1)
  .transform((s) => s as ToolId);
const workspaceIdSchema = z
  .string()
  .min(1)
  .transform((s) => s as WorkspaceId);

export const toolTypeSchema = z.enum(["builtin", "http", "messaging", "agent_handoff", "webhook", "python", "mock"]);

export const toolStatusSchema = z.enum(["draft", "active", "disabled", "archived"]);

const jsonbSchema = z.record(z.string(), z.unknown());

const toolSummaryWireSchema = z.object({
  id: toolIdSchema,
  name: z.string(),
  slug: z.string(),
  description: z.string(),
  type: toolTypeSchema,
  category: z.string(),
  icon: z.string().nullable().optional(),
  status: toolStatusSchema,
  version: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
});

export function toToolSummary(t: z.infer<typeof toolSummaryWireSchema>): ToolSummary {
  return {
    id: t.id,
    name: t.name,
    slug: t.slug,
    description: t.description,
    type: t.type,
    category: t.category,
    icon: t.icon ?? undefined,
    status: t.status,
    version: t.version,
    createdAt: t.created_at,
    updatedAt: t.updated_at,
  };
}

const toolDetailWireSchema = z.object({
  id: toolIdSchema,
  workspace_id: workspaceIdSchema.nullable().optional(),
  name: z.string(),
  slug: z.string(),
  description: z.string(),
  type: toolTypeSchema,
  category: z.string(),
  icon: z.string().nullable().optional(),
  status: toolStatusSchema,
  version: z.number(),
  input_schema: jsonbSchema.default({}),
  output_schema: jsonbSchema.default({}),
  config: jsonbSchema.default({}),
  auth: jsonbSchema.default({}),
  guardrails: jsonbSchema.default({}),
  execution_policy: jsonbSchema.default({}),
  channels: jsonbSchema.default({}),
  created_by: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export function toToolDetail(t: z.infer<typeof toolDetailWireSchema>): ToolDetail {
  return {
    id: t.id,
    workspaceId: t.workspace_id ?? undefined,
    name: t.name,
    slug: t.slug,
    description: t.description,
    type: t.type,
    category: t.category,
    icon: t.icon ?? undefined,
    status: t.status,
    version: t.version,
    inputSchema: t.input_schema,
    outputSchema: t.output_schema,
    config: t.config,
    auth: t.auth,
    guardrails: t.guardrails,
    executionPolicy: t.execution_policy,
    channels: t.channels,
    createdBy: t.created_by ?? undefined,
    createdAt: t.created_at,
    updatedAt: t.updated_at,
  };
}

const toolVersionSummaryWireSchema = z.object({
  id: z.string(),
  tool_id: toolIdSchema,
  version_number: z.number(),
  name: z.string(),
  type: toolTypeSchema,
  created_at: z.string(),
  created_by: z.string().nullable().optional(),
});

export function toToolVersionSummary(v: z.infer<typeof toolVersionSummaryWireSchema>): ToolVersionSummary {
  return {
    id: v.id,
    toolId: v.tool_id,
    versionNumber: v.version_number,
    name: v.name,
    type: v.type,
    createdAt: v.created_at,
    createdBy: v.created_by ?? undefined,
  };
}

export { toolSummaryWireSchema, toolDetailWireSchema, toolVersionSummaryWireSchema };
