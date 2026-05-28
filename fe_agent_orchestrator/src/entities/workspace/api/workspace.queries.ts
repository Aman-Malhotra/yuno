import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { workspaceApi, type CreateWorkspaceInput } from "./workspace.service";
import type { WorkspaceId } from "../model/workspace.types";

export const workspaceQueryKeys = {
  all: ["workspaces"] as const,
  lists: () => [...workspaceQueryKeys.all, "list"] as const,
  list: (page: number, pageSize: number) => [...workspaceQueryKeys.lists(), page, pageSize] as const,
} as const;

export function useWorkspaces(page = 1, pageSize = 50) {
  return useQuery({
    queryKey: workspaceQueryKeys.list(page, pageSize),
    queryFn: () => workspaceApi.list({ page, pageSize }),
  });
}

export function useCreateWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateWorkspaceInput) => workspaceApi.create(input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: workspaceQueryKeys.lists() });
    },
  });
}

export function useDeleteWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (workspaceId: WorkspaceId) => workspaceApi.delete(workspaceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: workspaceQueryKeys.lists() });
    },
  });
}
