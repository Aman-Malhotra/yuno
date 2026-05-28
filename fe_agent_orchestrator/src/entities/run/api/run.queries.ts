import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { WorkflowId } from "@/entities/workflow";
import type { WorkspaceId } from "@/entities/workspace";

import { runApi } from "./run.service";
import type { RunId, RunStatus } from "../model/run.types";

export const runQueryKeys = {
  all: ["runs"] as const,
  inWorkspace: (ws: WorkspaceId) => [...runQueryKeys.all, "in-workspace", ws] as const,
  list: (
    ws: WorkspaceId,
    workflowId: WorkflowId | undefined,
    status: RunStatus | undefined,
    page: number,
    pageSize: number,
  ) =>
    [
      ...runQueryKeys.inWorkspace(ws),
      { workflowId: workflowId ?? null, status: status ?? null, page, pageSize },
    ] as const,
  detail: (ws: WorkspaceId, runId: RunId) => [...runQueryKeys.all, "detail", ws, runId] as const,
} as const;

export function useRuns(
  workspaceId: WorkspaceId,
  options: {
    workflowId?: WorkflowId;
    status?: RunStatus;
    page?: number;
    pageSize?: number;
    refetchInterval?: number | false;
  } = {},
) {
  const { workflowId, status, page = 1, pageSize = 25, refetchInterval } = options;
  return useQuery({
    queryKey: runQueryKeys.list(workspaceId, workflowId, status, page, pageSize),
    queryFn: () => runApi.listInWorkspace(workspaceId, { workflowId, status, page, pageSize }),
    enabled: Boolean(workspaceId),
    refetchInterval,
  });
}

export function useRun(
  workspaceId: WorkspaceId,
  runId: RunId | undefined,
  options: { refetchInterval?: number | false } = {},
) {
  return useQuery({
    queryKey: runId ? runQueryKeys.detail(workspaceId, runId) : runQueryKeys.all,
    queryFn: () => runApi.getById(workspaceId, runId!),
    enabled: Boolean(workspaceId && runId),
    refetchInterval: options.refetchInterval,
  });
}

export function useCancelRun(workspaceId: WorkspaceId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: RunId) => runApi.cancel(workspaceId, runId),
    onSuccess: (_summary, runId) => {
      qc.invalidateQueries({ queryKey: runQueryKeys.inWorkspace(workspaceId) });
      qc.invalidateQueries({ queryKey: runQueryKeys.detail(workspaceId, runId) });
    },
  });
}

export function useDeleteRun(workspaceId: WorkspaceId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: RunId) => runApi.delete(workspaceId, runId),
    onSuccess: (_void, runId) => {
      qc.removeQueries({ queryKey: runQueryKeys.detail(workspaceId, runId) });
      qc.invalidateQueries({ queryKey: runQueryKeys.inWorkspace(workspaceId) });
    },
  });
}

/**
 * POST /workspaces/{ws}/workflows/{wf}/runs — operator-triggered test run.
 *
 * Returns a RunSummary; caller should immediately seed a polling
 * `useRun(runId, { refetchInterval: 1000 })` to drive the live status overlay.
 */
export function useCreateTestRun(workspaceId: WorkspaceId, workflowId: WorkflowId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: Record<string, unknown>) =>
      runApi.triggerManual(workspaceId, workflowId, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: runQueryKeys.inWorkspace(workspaceId) });
    },
  });
}
