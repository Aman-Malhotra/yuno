import { z } from "zod";
import type { WorkspaceId } from "@/entities/workspace";
import type {
  WorkspaceCredentialId,
  WorkspaceCredentialSummary,
} from "./workspace-llm-provider.types";

const credentialIdSchema = z
  .string()
  .min(1)
  .transform((s) => s as WorkspaceCredentialId);

const workspaceIdSchema = z
  .string()
  .min(1)
  .transform((s) => s as WorkspaceId);

export const workspaceCredentialWireSchema = z.object({
  id: credentialIdSchema,
  workspace_id: workspaceIdSchema,
  provider: z.string(),
  last4: z.string(),
  base_url: z.string().nullable().optional(),
  organization: z.string().nullable().optional(),
  created_by: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const workspaceCredentialListWireSchema = z.object({
  items: z.array(workspaceCredentialWireSchema),
});

export function toWorkspaceCredentialSummary(
  w: z.infer<typeof workspaceCredentialWireSchema>,
): WorkspaceCredentialSummary {
  return {
    id: w.id,
    workspaceId: w.workspace_id,
    provider: w.provider,
    last4: w.last4,
    baseUrl: w.base_url ?? undefined,
    organization: w.organization ?? undefined,
    createdBy: w.created_by ?? undefined,
    createdAt: w.created_at,
    updatedAt: w.updated_at,
  };
}
