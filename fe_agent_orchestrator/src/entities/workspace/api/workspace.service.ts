import { z } from "zod";
import { ApiService, pageResponseSchema, type PageResponse } from "@/shared/api";
import { toWorkspaceSummary, workspaceSummaryWireSchema } from "../model/workspace.schema";
import type { WorkspaceId, WorkspaceSummary } from "../model/workspace.types";

type ListParams = { page?: number; pageSize?: number };

export type CreateWorkspaceInput = {
  name: string;
};

class WorkspaceService extends ApiService {
  constructor() {
    super("/workspaces");
  }

  list = async (params: ListParams = {}): Promise<PageResponse<WorkspaceSummary>> => {
    const q = new URLSearchParams();
    if (params.page) q.set("page", String(params.page));
    if (params.pageSize) q.set("page_size", String(params.pageSize));
    const qs = q.toString();
    const wire = await this._get(qs ? `/?${qs}` : "/", pageResponseSchema(workspaceSummaryWireSchema));
    return {
      ...wire,
      items: wire.items.map(toWorkspaceSummary),
    };
  };

  /** POST /api/v1/workspaces/ — server generates slug + id, returns the new summary. */
  create = async (input: CreateWorkspaceInput): Promise<WorkspaceSummary> => {
    const wire = await this._post("/", { name: input.name }, workspaceSummaryWireSchema);
    return toWorkspaceSummary(wire);
  };

  /**
   * DELETE /api/v1/workspaces/{id} — owner-only soft delete. 204 on success;
   * disappears from `list` immediately, nested endpoints return 403 after.
   */
  delete = (workspaceId: WorkspaceId): Promise<void> => this._delete(`/${workspaceId}`, z.void());
}

export const workspaceApi = new WorkspaceService();
