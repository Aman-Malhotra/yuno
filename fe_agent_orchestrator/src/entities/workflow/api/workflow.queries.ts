import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { WorkspaceId } from "@/entities/workspace";
import type {
  CreateWorkflowInput,
  UpdateWorkflowInput,
  Workflow,
  WorkflowGraph,
  WorkflowId,
} from "../model/workflow.types";
import { workflowApi } from "./workflow.service";

export const workflowQueryKeys = {
  all: ["workflows"] as const,
  inWorkspace: (id: WorkspaceId) => [...workflowQueryKeys.all, "in-workspace", id] as const,
  inWorkspaceList: (id: WorkspaceId, page: number, pageSize: number) =>
    [...workflowQueryKeys.inWorkspace(id), page, pageSize] as const,
  detail: (ws: WorkspaceId, id: WorkflowId) => [...workflowQueryKeys.all, "detail", ws, id] as const,
} as const;

export function useWorkflowsInWorkspace(workspaceId: WorkspaceId, page = 1, pageSize = 50) {
  return useQuery({
    queryKey: workflowQueryKeys.inWorkspaceList(workspaceId, page, pageSize),
    queryFn: () => workflowApi.listInWorkspace(workspaceId, { page, pageSize }),
    enabled: Boolean(workspaceId),
  });
}

/** Full workflow incl. graph + compiled_graph — used by the builder page. */
export function useWorkflow(workspaceId: WorkspaceId, workflowId: WorkflowId | undefined) {
  return useQuery({
    queryKey: workflowId ? workflowQueryKeys.detail(workspaceId, workflowId) : workflowQueryKeys.all,
    queryFn: () => workflowApi.getById(workspaceId, workflowId!),
    enabled: Boolean(workspaceId && workflowId),
  });
}

export function useCreateWorkflow(workspaceId: WorkspaceId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateWorkflowInput) => workflowApi.create(workspaceId, input),
    onSuccess: (workflow: Workflow) => {
      // Seed the detail cache so the builder doesn't refetch on first mount.
      qc.setQueryData(workflowQueryKeys.detail(workspaceId, workflow.id), workflow);
      qc.invalidateQueries({ queryKey: workflowQueryKeys.inWorkspace(workspaceId) });
    },
  });
}

export function useUpdateWorkflow(workspaceId: WorkspaceId, workflowId: WorkflowId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateWorkflowInput) => workflowApi.update(workspaceId, workflowId, input),
    onSuccess: (workflow: Workflow) => {
      qc.setQueryData(workflowQueryKeys.detail(workspaceId, workflow.id), workflow);
      qc.invalidateQueries({ queryKey: workflowQueryKeys.inWorkspace(workspaceId) });
    },
  });
}

/**
 * Autosave mutation for the React Flow canvas — replaces `graph_json` and
 * re-derives `compiled_graph` on the server. Call sites debounce.
 */
export function useUpdateWorkflowGraph(workspaceId: WorkspaceId, workflowId: WorkflowId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (graph: WorkflowGraph) => workflowApi.updateGraph(workspaceId, workflowId, graph),
    onSuccess: (workflow: Workflow) => {
      qc.setQueryData(workflowQueryKeys.detail(workspaceId, workflow.id), workflow);
    },
  });
}

export function useDeleteWorkflow(workspaceId: WorkspaceId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (workflowId: WorkflowId) => workflowApi.delete(workspaceId, workflowId),
    onSuccess: (_void, workflowId) => {
      qc.removeQueries({ queryKey: workflowQueryKeys.detail(workspaceId, workflowId) });
      qc.invalidateQueries({ queryKey: workflowQueryKeys.inWorkspace(workspaceId) });
    },
  });
}
