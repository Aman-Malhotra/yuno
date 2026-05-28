import type { Brand } from "@/shared/types/brand";

export type WorkspaceId = Brand<string, "WorkspaceId">;

export type WorkspaceRole = "owner" | "admin" | "member" | "viewer";

export type WorkspaceSummary = {
  id: WorkspaceId;
  name: string;
  slug: string;
  role: WorkspaceRole;
  createdAt: string;
};
