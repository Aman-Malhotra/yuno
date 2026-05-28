import { z } from "zod";

import type { WorkflowId } from "@/entities/workflow";
import type { WorkspaceId } from "@/entities/workspace";

import type { WebhookCreated, WebhookId, WebhookSummary } from "./webhook.types";

const webhookIdSchema = z
  .string()
  .min(1)
  .transform((s) => s as WebhookId);
const workspaceIdSchema = z
  .string()
  .min(1)
  .transform((s) => s as WorkspaceId);
const workflowIdSchema = z
  .string()
  .min(1)
  .transform((s) => s as WorkflowId);

export const webhookStatusSchema = z.enum(["active", "revoked"]);

export const webhookSummaryWireSchema = z.object({
  id: webhookIdSchema,
  workspace_id: workspaceIdSchema,
  workflow_id: workflowIdSchema,
  name: z.string(),
  status: webhookStatusSchema,
  token_prefix: z.string(),
  last_used_at: z.string().nullable().optional(),
  last_used_ip: z.string().nullable().optional(),
  last_error: z.string().nullable().optional(),
  created_by: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const webhookCreatedWireSchema = webhookSummaryWireSchema.extend({
  token: z.string(),
  url: z.string(),
});

export function toWebhookSummary(w: z.infer<typeof webhookSummaryWireSchema>): WebhookSummary {
  return {
    id: w.id,
    workspaceId: w.workspace_id,
    workflowId: w.workflow_id,
    name: w.name,
    status: w.status,
    tokenPrefix: w.token_prefix,
    lastUsedAt: w.last_used_at ?? undefined,
    lastUsedIp: w.last_used_ip ?? undefined,
    lastError: w.last_error ?? undefined,
    createdBy: w.created_by ?? undefined,
    createdAt: w.created_at,
    updatedAt: w.updated_at,
  };
}

export function toWebhookCreated(w: z.infer<typeof webhookCreatedWireSchema>): WebhookCreated {
  return {
    ...toWebhookSummary(w),
    token: w.token,
    url: w.url,
  };
}
