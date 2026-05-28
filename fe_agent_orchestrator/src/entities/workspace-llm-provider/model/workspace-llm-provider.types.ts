import type { WorkspaceId } from "@/entities/workspace";

/** Opaque workspace-credential row id from the backend. */
export type WorkspaceCredentialId = string & { readonly __brand: "WorkspaceCredentialId" };

export interface WorkspaceCredentialSummary {
  id: WorkspaceCredentialId;
  workspaceId: WorkspaceId;
  provider: string;
  /** Last four characters of the api_key, prefixed with `…` — backend never returns the full key. */
  last4: string;
  baseUrl?: string;
  organization?: string;
  createdBy?: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateWorkspaceCredentialInput {
  provider: string;
  apiKey: string;
  baseUrl?: string;
  organization?: string;
}

export interface UpdateWorkspaceCredentialInput {
  apiKey?: string;
  baseUrl?: string;
  organization?: string;
}
