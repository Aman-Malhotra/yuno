import { z } from "zod";
import { ApiService, pageResponseSchema, type PageResponse } from "@/shared/api";
import type { WorkspaceId } from "@/entities/workspace";
import {
  toCreateWorkflowBody,
  toUpdateWorkflowBody,
  toWorkflow,
  toWorkflowGraphWire,
  toWorkflowSummary,
  workflowDetailWireSchema,
  workflowSummaryWireSchema,
} from "../model/workflow.schema";
import type {
  CreateWorkflowInput,
  UpdateWorkflowInput,
  Workflow,
  WorkflowGraph,
  WorkflowId,
  WorkflowSummary,
} from "../model/workflow.types";

type ListInWorkspaceParams = { page?: number; pageSize?: number };

class WorkflowService extends ApiService {
  constructor() {
    super("/workspaces");
  }

  /** GET /api/v1/workspaces/{ws}/workflows/ */
  listInWorkspace = async (
    workspaceId: WorkspaceId,
    params: ListInWorkspaceParams = {},
  ): Promise<PageResponse<WorkflowSummary>> => {
    const q = new URLSearchParams();
    if (params.page) q.set("page", String(params.page));
    if (params.pageSize) q.set("page_size", String(params.pageSize));
    const qs = q.toString();
    const wire = await this._get(
      `/${workspaceId}/workflows/${qs ? `?${qs}` : ""}`,
      pageResponseSchema(workflowSummaryWireSchema),
    );
    return {
      ...wire,
      items: wire.items.map(toWorkflowSummary),
    };
  };

  /** POST /api/v1/workspaces/{ws}/workflows/ */
  create = async (workspaceId: WorkspaceId, input: CreateWorkflowInput): Promise<Workflow> => {
    const wire = await this._post(`/${workspaceId}/workflows/`, toCreateWorkflowBody(input), workflowDetailWireSchema);
    return toWorkflow(wire);
  };

  /** GET /api/v1/workspaces/{ws}/workflows/{id} */
  getById = async (workspaceId: WorkspaceId, workflowId: WorkflowId): Promise<Workflow> => {
    const wire = await this._get(`/${workspaceId}/workflows/${workflowId}`, workflowDetailWireSchema);
    return toWorkflow(wire);
  };

  /** PATCH /api/v1/workspaces/{ws}/workflows/{id} — metadata only. */
  update = async (workspaceId: WorkspaceId, workflowId: WorkflowId, input: UpdateWorkflowInput): Promise<Workflow> => {
    const wire = await this._patch(
      `/${workspaceId}/workflows/${workflowId}`,
      toUpdateWorkflowBody(input),
      workflowDetailWireSchema,
    );
    return toWorkflow(wire);
  };

  /**
   * PATCH /api/v1/workspaces/{ws}/workflows/{id}/graph — autosave path.
   *
   * Replaces the entire graph and re-derives the langgraph-ready compiled
   * shape server-side. Permissive: in-progress graphs (missing end node,
   * agent nodes without an `agentId`) are tolerated. Only agent refs that
   * *are* set must belong to the workspace.
   */
  updateGraph = async (workspaceId: WorkspaceId, workflowId: WorkflowId, graph: WorkflowGraph): Promise<Workflow> => {
    const wire = await this._patch(
      `/${workspaceId}/workflows/${workflowId}/graph`,
      { graph: toWorkflowGraphWire(graph) },
      workflowDetailWireSchema,
    );
    return toWorkflow(wire);
  };

  /** DELETE /api/v1/workspaces/{ws}/workflows/{id} — soft delete. */
  delete = async (workspaceId: WorkspaceId, workflowId: WorkflowId): Promise<void> => {
    await this._delete(`/${workspaceId}/workflows/${workflowId}`, z.void());
  };
}

export const workflowApi = new WorkflowService();
