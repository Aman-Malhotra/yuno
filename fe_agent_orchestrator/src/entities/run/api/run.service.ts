import { z } from "zod";

import { ApiService, pageResponseSchema, type PageResponse } from "@/shared/api";
import type { WorkflowId } from "@/entities/workflow";
import type { WorkspaceId } from "@/entities/workspace";

import {
  runDetailWireSchema,
  runSummaryWireSchema,
  toRunDetail,
  toRunSummary,
} from "../model/run.schema";
import type { RunDetail, RunId, RunStatus, RunSummary } from "../model/run.types";

type ListParams = {
  page?: number;
  pageSize?: number;
  workflowId?: WorkflowId;
  status?: RunStatus;
};

class RunService extends ApiService {
  constructor() {
    super("/workspaces");
  }

  /** GET /api/v1/workspaces/{ws}/runs/ */
  listInWorkspace = async (
    workspaceId: WorkspaceId,
    params: ListParams = {},
  ): Promise<PageResponse<RunSummary>> => {
    const q = new URLSearchParams();
    if (params.page) q.set("page", String(params.page));
    if (params.pageSize) q.set("page_size", String(params.pageSize));
    if (params.workflowId) q.set("workflow_id", params.workflowId);
    if (params.status) q.set("status", params.status);
    const qs = q.toString();
    const wire = await this._get(
      `/${workspaceId}/runs/${qs ? `?${qs}` : ""}`,
      pageResponseSchema(runSummaryWireSchema),
    );
    return { ...wire, items: wire.items.map(toRunSummary) };
  };

  /** GET /api/v1/workspaces/{ws}/runs/{run_id} */
  getById = async (workspaceId: WorkspaceId, runId: RunId): Promise<RunDetail> => {
    const wire = await this._get(`/${workspaceId}/runs/${runId}`, runDetailWireSchema);
    return toRunDetail(wire);
  };

  /** POST /api/v1/workspaces/{ws}/runs/{run_id}/cancel — abort queued/running. */
  cancel = async (workspaceId: WorkspaceId, runId: RunId): Promise<RunSummary> => {
    const wire = await this._post(
      `/${workspaceId}/runs/${runId}/cancel`,
      undefined,
      runSummaryWireSchema,
    );
    return toRunSummary(wire);
  };

  /** DELETE /api/v1/workspaces/{ws}/runs/{run_id} — hard delete + cascade. */
  delete = async (workspaceId: WorkspaceId, runId: RunId): Promise<void> => {
    await this._delete(`/${workspaceId}/runs/${runId}`, z.void());
  };

  /**
   * POST /workspaces/{ws}/workflows/{wf}/runs — operator-triggered test run.
   *
   * Body is opaque JSON passed straight to the executor as initial state.
   * The trigger_type is stamped 'test' server-side so this run never gets
   * confused with channel-driven traffic in the Runs/Logs/Costs UIs.
   */
  triggerManual = async (
    workspaceId: WorkspaceId,
    workflowId: WorkflowId,
    input: Record<string, unknown>,
  ): Promise<RunSummary> => {
    const wire = await this._post(
      `/${workspaceId}/workflows/${workflowId}/runs`,
      input,
      runSummaryWireSchema,
    );
    return toRunSummary(wire);
  };
}

export const runApi = new RunService();
