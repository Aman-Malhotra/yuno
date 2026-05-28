import { z } from "zod";

import { ApiService } from "@/shared/api";
import type { WorkflowId } from "@/entities/workflow";
import type { WorkspaceId } from "@/entities/workspace";

import {
  toWebhookCreated,
  toWebhookSummary,
  webhookCreatedWireSchema,
  webhookSummaryWireSchema,
} from "../model/webhook.schema";
import type {
  CreateWebhookInput,
  WebhookCreated,
  WebhookId,
  WebhookSummary,
} from "../model/webhook.types";

const listSchema = z.array(webhookSummaryWireSchema);

class WebhookService extends ApiService {
  constructor() {
    super("/workspaces");
  }

  /** GET /api/v1/workspaces/{ws}/workflows/{wf}/webhooks/ */
  listForWorkflow = async (
    workspaceId: WorkspaceId,
    workflowId: WorkflowId,
  ): Promise<WebhookSummary[]> => {
    const wire = await this._get(`/${workspaceId}/workflows/${workflowId}/webhooks/`, listSchema);
    return wire.map(toWebhookSummary);
  };

  /** POST /api/v1/workspaces/{ws}/workflows/{wf}/webhooks/ — plaintext token returned once. */
  create = async (
    workspaceId: WorkspaceId,
    workflowId: WorkflowId,
    input: CreateWebhookInput,
  ): Promise<WebhookCreated> => {
    const wire = await this._post(
      `/${workspaceId}/workflows/${workflowId}/webhooks/`,
      input,
      webhookCreatedWireSchema,
    );
    return toWebhookCreated(wire);
  };

  /** DELETE /api/v1/workspaces/{ws}/workflows/{wf}/webhooks/{id} — idempotent revoke. */
  revoke = async (
    workspaceId: WorkspaceId,
    workflowId: WorkflowId,
    webhookId: WebhookId,
  ): Promise<void> => {
    await this._delete(
      `/${workspaceId}/workflows/${workflowId}/webhooks/${webhookId}`,
      z.void(),
    );
  };
}

export const webhookApi = new WebhookService();
