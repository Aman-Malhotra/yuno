import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { WorkspaceId } from "@/entities/workspace";
import { agentApi } from "./agent.service";
import type { AgentId, CreateAgentInput, UpdateAgentInput } from "../model/agent.types";

export const agentQueryKeys = {
  all: ["agents"] as const,
  inWorkspace: (id: WorkspaceId) => [...agentQueryKeys.all, "in-workspace", id] as const,
  inWorkspaceList: (id: WorkspaceId, page: number, pageSize: number) =>
    [...agentQueryKeys.inWorkspace(id), page, pageSize] as const,
  detail: (id: WorkspaceId, agentId: AgentId) => [...agentQueryKeys.all, "detail", id, agentId] as const,
  capabilities: () => [...agentQueryKeys.all, "capabilities"] as const,
  capabilitiesForWorkspace: (id: WorkspaceId) =>
    [...agentQueryKeys.all, "capabilities-for-workspace", id] as const,
} as const;

export function useAgentsInWorkspace(workspaceId: WorkspaceId, page = 1, pageSize = 50) {
  return useQuery({
    queryKey: agentQueryKeys.inWorkspaceList(workspaceId, page, pageSize),
    queryFn: () => agentApi.listInWorkspace(workspaceId, { page, pageSize }),
    enabled: Boolean(workspaceId),
  });
}

/** GET /workspaces/{ws}/agents/{id} — full configuration including JSONB blobs. */
export function useAgent(workspaceId: WorkspaceId, agentId: AgentId) {
  return useQuery({
    queryKey: agentQueryKeys.detail(workspaceId, agentId),
    queryFn: () => agentApi.getById(workspaceId, agentId),
    enabled: Boolean(workspaceId && agentId),
  });
}

/** GET /agents/capabilities — providers, models, field constraints, tools. */
export function useAgentCapabilities(enabled = true) {
  return useQuery({
    queryKey: agentQueryKeys.capabilities(),
    queryFn: () => agentApi.getCapabilities(),
    staleTime: 5 * 60_000,
    enabled,
  });
}

/**
 * GET /workspaces/{ws}/agents/capabilities — workspace-aware capabilities.
 *
 * `is_configured` flips true for providers that have a workspace-default
 * credential in addition to the per-user vault check. Use this in the
 * agent-create form so users see which providers their workspace already
 * covers without per-agent BYOK.
 */
export function useAgentCapabilitiesForWorkspace(workspaceId: WorkspaceId, enabled = true) {
  return useQuery({
    queryKey: agentQueryKeys.capabilitiesForWorkspace(workspaceId),
    queryFn: () => agentApi.getCapabilitiesForWorkspace(workspaceId),
    staleTime: 60_000,
    enabled: enabled && Boolean(workspaceId),
  });
}

export function useCreateAgent(workspaceId: WorkspaceId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateAgentInput) => agentApi.create(workspaceId, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: agentQueryKeys.inWorkspace(workspaceId) });
    },
  });
}

export function useUpdateAgent(workspaceId: WorkspaceId, agentId: AgentId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateAgentInput) => agentApi.update(workspaceId, agentId, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: agentQueryKeys.detail(workspaceId, agentId) });
      qc.invalidateQueries({ queryKey: agentQueryKeys.inWorkspace(workspaceId) });
    },
  });
}
