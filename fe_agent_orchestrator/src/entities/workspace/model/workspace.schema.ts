import { z } from "zod";
import type { WorkspaceId, WorkspaceSummary } from "./workspace.types";

const workspaceIdSchema = z
  .string()
  .min(1)
  .transform((s) => s as WorkspaceId);

export const workspaceRoleSchema = z.enum(["owner", "admin", "member", "viewer"]);

/** Wire shape from GET /workspaces (snake_case). */
const workspaceSummaryWireSchema = z.object({
  id: workspaceIdSchema,
  name: z.string(),
  slug: z.string(),
  role: workspaceRoleSchema,
  created_at: z.string(),
});

export function toWorkspaceSummary(w: z.infer<typeof workspaceSummaryWireSchema>): WorkspaceSummary {
  return {
    id: w.id,
    name: w.name,
    slug: w.slug,
    role: w.role,
    createdAt: w.created_at,
  };
}

export { workspaceSummaryWireSchema };
