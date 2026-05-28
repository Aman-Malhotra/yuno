import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { WorkflowId } from "@/entities/workflow";
import type { WorkspaceId } from "@/entities/workspace";

import { webhookApi } from "./webhook.service";
import type { CreateWebhookInput, WebhookId } from "../model/webhook.types";

export const webhookQueryKeys = {
  all: ["webhooks"] as const,
  forWorkflow: (ws: WorkspaceId, wf: WorkflowId) =>
    [...webhookQueryKeys.all, "for-workflow", ws, wf] as const,
} as const;

export function useWebhooksForWorkflow(workspaceId: WorkspaceId, workflowId: WorkflowId) {
  return useQuery({
    queryKey: webhookQueryKeys.forWorkflow(workspaceId, workflowId),
    queryFn: () => webhookApi.listForWorkflow(workspaceId, workflowId),
    enabled: Boolean(workspaceId && workflowId),
  });
}

export function useCreateWebhook(workspaceId: WorkspaceId, workflowId: WorkflowId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateWebhookInput) => webhookApi.create(workspaceId, workflowId, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: webhookQueryKeys.forWorkflow(workspaceId, workflowId) });
    },
  });
}

export function useRevokeWebhook(workspaceId: WorkspaceId, workflowId: WorkflowId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (webhookId: WebhookId) => webhookApi.revoke(workspaceId, workflowId, webhookId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: webhookQueryKeys.forWorkflow(workspaceId, workflowId) });
    },
  });
}
