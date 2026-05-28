import { z } from "zod";

// Mirrors openapi.yaml → CreateWorkspaceRequest (name: 1-255 chars, required).
export const createWorkspaceSchema = z.object({
  name: z.string().trim().min(1, "Name is required").max(255, "Max 255 characters"),
});

export type CreateWorkspaceInput = z.infer<typeof createWorkspaceSchema>;
