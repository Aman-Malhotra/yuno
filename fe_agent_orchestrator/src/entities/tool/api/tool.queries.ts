import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { WorkspaceId } from "@/entities/workspace";
import { toolApi } from "./tool.service";
import type { CreateToolInput, ToolId, UpdateToolInput } from "../model/tool.types";

export const toolQueryKeys = {
  all: ["tools"] as const,
  inWorkspace: (id: WorkspaceId) => [...toolQueryKeys.all, "in-workspace", id] as const,
  inWorkspaceList: (id: WorkspaceId, page: number, pageSize: number) =>
    [...toolQueryKeys.inWorkspace(id), page, pageSize] as const,
  detail: (id: WorkspaceId, toolId: ToolId) => [...toolQueryKeys.all, "detail", id, toolId] as const,
  versions: (id: WorkspaceId, toolId: ToolId) => [...toolQueryKeys.detail(id, toolId), "versions"] as const,
  builtins: (id: WorkspaceId) => [...toolQueryKeys.all, "builtins", id] as const,
} as const;

export function useToolsInWorkspace(workspaceId: WorkspaceId, page = 1, pageSize = 50) {
  return useQuery({
    queryKey: toolQueryKeys.inWorkspaceList(workspaceId, page, pageSize),
    queryFn: () => toolApi.listInWorkspace(workspaceId, { page, pageSize }),
    enabled: Boolean(workspaceId),
  });
}

export function useTool(workspaceId: WorkspaceId, toolId: ToolId) {
  return useQuery({
    queryKey: toolQueryKeys.detail(workspaceId, toolId),
    queryFn: () => toolApi.getById(workspaceId, toolId),
    enabled: Boolean(workspaceId && toolId),
  });
}

export function useToolVersions(workspaceId: WorkspaceId, toolId: ToolId, enabled = true) {
  return useQuery({
    queryKey: toolQueryKeys.versions(workspaceId, toolId),
    queryFn: () => toolApi.listVersions(workspaceId, toolId),
    enabled: enabled && Boolean(workspaceId && toolId),
  });
}

export function useToolBuiltins(workspaceId: WorkspaceId, enabled = true) {
  return useQuery({
    queryKey: toolQueryKeys.builtins(workspaceId),
    queryFn: () => toolApi.listBuiltins(workspaceId),
    enabled: enabled && Boolean(workspaceId),
    staleTime: 5 * 60_000,
  });
}

export function useCreateTool(workspaceId: WorkspaceId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateToolInput) => toolApi.create(workspaceId, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: toolQueryKeys.inWorkspace(workspaceId) });
    },
  });
}

export function useUpdateTool(workspaceId: WorkspaceId, toolId: ToolId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateToolInput) => toolApi.update(workspaceId, toolId, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: toolQueryKeys.detail(workspaceId, toolId) });
      qc.invalidateQueries({ queryKey: toolQueryKeys.inWorkspace(workspaceId) });
      qc.invalidateQueries({ queryKey: toolQueryKeys.versions(workspaceId, toolId) });
    },
  });
}

export function useDeleteTool(workspaceId: WorkspaceId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (toolId: ToolId) => toolApi.delete(workspaceId, toolId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: toolQueryKeys.inWorkspace(workspaceId) });
    },
  });
}
