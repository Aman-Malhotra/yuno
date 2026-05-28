import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { WorkspaceId } from "@/entities/workspace";

import { memoryApi } from "./memory.service";
import type { MemoryId } from "../model/memory.types";

export const memoryQueryKeys = {
  all: ["memories"] as const,
  inWorkspace: (id: WorkspaceId) => [...memoryQueryKeys.all, "in-workspace", id] as const,
  list: (id: WorkspaceId, userId: string, username?: string) =>
    [...memoryQueryKeys.inWorkspace(id), "list", userId, username ?? null] as const,
  graph: (id: WorkspaceId, userId: string) =>
    [...memoryQueryKeys.inWorkspace(id), "graph", userId] as const,
} as const;

/** Long-term memories tagged to a channel user id. */
export function useMemoriesForUser(
  workspaceId: WorkspaceId,
  userId: string,
  username?: string,
  enabled = true,
) {
  return useQuery({
    queryKey: memoryQueryKeys.list(workspaceId, userId, username),
    queryFn: () => memoryApi.list({ workspaceId, userId, username }),
    enabled: enabled && Boolean(workspaceId && userId),
  });
}

/** Entity-relation graph projection for a user. */
export function useMemoryGraph(workspaceId: WorkspaceId, userId: string, enabled = true) {
  return useQuery({
    queryKey: memoryQueryKeys.graph(workspaceId, userId),
    queryFn: () => memoryApi.graph({ workspaceId, userId }),
    enabled: enabled && Boolean(workspaceId && userId),
  });
}

export function useDeleteMemory(workspaceId: WorkspaceId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (memoryId: MemoryId) => memoryApi.delete(workspaceId, memoryId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: memoryQueryKeys.inWorkspace(workspaceId) });
    },
  });
}
