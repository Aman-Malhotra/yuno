import type { Brand } from "@/shared/types/brand";
import type { WorkflowId } from "@/entities/workflow";
import type { WorkspaceId } from "@/entities/workspace";

export type WebhookId = Brand<string, "WebhookId">;

export type WebhookStatus = "active" | "revoked";

/** Light row shape returned by list + after-create. Never carries the plaintext token. */
export type WebhookSummary = {
  id: WebhookId;
  workspaceId: WorkspaceId;
  workflowId: WorkflowId;
  name: string;
  status: WebhookStatus;
  tokenPrefix: string;
  lastUsedAt?: string;
  lastUsedIp?: string;
  lastError?: string;
  createdBy?: string;
  createdAt: string;
  updatedAt: string;
};

/**
 * One-shot create response — plaintext `token` + `url` only shown here,
 * never again. After this mounts, persist nothing client-side; the user
 * is expected to copy and paste into their integration immediately.
 */
export type WebhookCreated = WebhookSummary & {
  token: string;
  url: string;
};

export type CreateWebhookInput = {
  name: string;
};
