import { useQuery } from "@tanstack/react-query";

import type { WorkspaceId } from "@/entities/workspace";

import { costApi } from "./cost.service";

export const costQueryKeys = {
  all: ["costs"] as const,
  inWorkspace: (id: WorkspaceId) => [...costQueryKeys.all, "in-workspace", id] as const,
  perAgent: (id: WorkspaceId, since?: string) =>
    [...costQueryKeys.inWorkspace(id), "per-agent", since ?? null] as const,
} as const;

export function useAgentCosts(workspaceId: WorkspaceId, since?: string, enabled = true) {
  return useQuery({
    queryKey: costQueryKeys.perAgent(workspaceId, since),
    queryFn: () => costApi.perAgent(workspaceId, since),
    enabled: enabled && Boolean(workspaceId),
    staleTime: 15_000,
  });
}
