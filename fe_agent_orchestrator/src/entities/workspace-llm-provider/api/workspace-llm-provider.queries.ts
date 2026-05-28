import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { WorkspaceId } from "@/entities/workspace";

import { workspaceLlmProviderApi } from "./workspace-llm-provider.service";
import type {
  CreateWorkspaceCredentialInput,
  UpdateWorkspaceCredentialInput,
  WorkspaceCredentialId,
} from "../model/workspace-llm-provider.types";

export const workspaceLlmProviderQueryKeys = {
  all: ["workspace-llm-providers"] as const,
  inWorkspace: (id: WorkspaceId) => [...workspaceLlmProviderQueryKeys.all, "in-workspace", id] as const,
} as const;

export function useWorkspaceLlmProviders(workspaceId: WorkspaceId, enabled = true) {
  return useQuery({
    queryKey: workspaceLlmProviderQueryKeys.inWorkspace(workspaceId),
    queryFn: () => workspaceLlmProviderApi.list(workspaceId),
    enabled: enabled && Boolean(workspaceId),
  });
}

export function useCreateWorkspaceLlmProvider(workspaceId: WorkspaceId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateWorkspaceCredentialInput) =>
      workspaceLlmProviderApi.create(workspaceId, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: workspaceLlmProviderQueryKeys.inWorkspace(workspaceId) });
    },
  });
}

export function useUpdateWorkspaceLlmProvider(workspaceId: WorkspaceId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { credentialId: WorkspaceCredentialId; input: UpdateWorkspaceCredentialInput }) =>
      workspaceLlmProviderApi.update(workspaceId, vars.credentialId, vars.input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: workspaceLlmProviderQueryKeys.inWorkspace(workspaceId) });
    },
  });
}

export function useDeleteWorkspaceLlmProvider(workspaceId: WorkspaceId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (credentialId: WorkspaceCredentialId) =>
      workspaceLlmProviderApi.delete(workspaceId, credentialId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: workspaceLlmProviderQueryKeys.inWorkspace(workspaceId) });
    },
  });
}
