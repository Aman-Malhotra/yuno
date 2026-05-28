import { z } from "zod";
import { ApiService, pageResponseSchema, type PageResponse } from "@/shared/api";
import type { WorkspaceId } from "@/entities/workspace";

import {
  toolDetailWireSchema,
  toolSummaryWireSchema,
  toolVersionSummaryWireSchema,
  toToolDetail,
  toToolSummary,
  toToolVersionSummary,
} from "../model/tool.schema";
import type {
  CreateToolInput,
  ToolDetail,
  ToolId,
  ToolSummary,
  ToolType,
  ToolStatus,
  ToolVersionSummary,
  UpdateToolInput,
} from "../model/tool.types";

type ListParams = {
  page?: number;
  pageSize?: number;
  type?: ToolType;
  category?: string;
  status?: ToolStatus;
};

class ToolService extends ApiService {
  constructor() {
    super("/workspaces");
  }

  /** GET /workspaces/{ws}/tools/ — workspace tools + global built-ins. */
  listInWorkspace = async (workspaceId: WorkspaceId, params: ListParams = {}): Promise<PageResponse<ToolSummary>> => {
    const q = new URLSearchParams();
    if (params.page) q.set("page", String(params.page));
    if (params.pageSize) q.set("page_size", String(params.pageSize));
    if (params.type) q.set("type", params.type);
    if (params.category) q.set("category", params.category);
    if (params.status) q.set("status", params.status);
    const qs = q.toString();
    const wire = await this._get(
      `/${workspaceId}/tools/${qs ? `?${qs}` : ""}`,
      pageResponseSchema(toolSummaryWireSchema),
    );
    return { ...wire, items: wire.items.map(toToolSummary) };
  };

  /** GET /workspaces/{ws}/tools/builtins — opaque per spec; returns raw entries. */
  listBuiltins = async (workspaceId: WorkspaceId): Promise<Record<string, unknown>[]> => {
    return this._get(`/${workspaceId}/tools/builtins`, z.array(z.record(z.string(), z.unknown())));
  };

  /** POST /workspaces/{ws}/tools/ → 201 ToolDetail */
  create = async (workspaceId: WorkspaceId, input: CreateToolInput): Promise<ToolDetail> => {
    const body = {
      name: input.name,
      description: input.description,
      type: input.type,
      category: input.category,
      icon: input.icon,
      input_schema: input.inputSchema,
      output_schema: input.outputSchema,
      config: input.config,
      status: input.status,
    };
    const wire = await this._post(`/${workspaceId}/tools/`, body, toolDetailWireSchema);
    return toToolDetail(wire);
  };

  /** GET /workspaces/{ws}/tools/{id} */
  getById = async (workspaceId: WorkspaceId, toolId: ToolId): Promise<ToolDetail> => {
    const wire = await this._get(`/${workspaceId}/tools/${toolId}`, toolDetailWireSchema);
    return toToolDetail(wire);
  };

  /**
   * PATCH /workspaces/{ws}/tools/{id} — partial update.
   * Spec forbids unknown keys (`additionalProperties: false`) and excludes
   * `type` from the update payload, so we only send the fields the caller set.
   */
  update = async (workspaceId: WorkspaceId, toolId: ToolId, input: UpdateToolInput): Promise<ToolDetail> => {
    const body: Record<string, unknown> = {};
    if (input.name !== undefined) body.name = input.name;
    if (input.description !== undefined) body.description = input.description;
    if (input.category !== undefined) body.category = input.category;
    if (input.icon !== undefined) body.icon = input.icon;
    if (input.inputSchema !== undefined) body.input_schema = input.inputSchema;
    if (input.outputSchema !== undefined) body.output_schema = input.outputSchema;
    if (input.config !== undefined) body.config = input.config;
    if (input.status !== undefined) body.status = input.status;
    if (input.publishNewVersion !== undefined) body.publish_new_version = input.publishNewVersion;
    const wire = await this._patch(`/${workspaceId}/tools/${toolId}`, body, toolDetailWireSchema);
    return toToolDetail(wire);
  };

  /** DELETE /workspaces/{ws}/tools/{id} */
  delete = (workspaceId: WorkspaceId, toolId: ToolId): Promise<void> =>
    this._delete(`/${workspaceId}/tools/${toolId}`, z.void());

  /** GET /workspaces/{ws}/tools/{id}/versions */
  listVersions = async (workspaceId: WorkspaceId, toolId: ToolId): Promise<ToolVersionSummary[]> => {
    const wire = await this._get(`/${workspaceId}/tools/${toolId}/versions`, z.array(toolVersionSummaryWireSchema));
    return wire.map(toToolVersionSummary);
  };
}

export const toolApi = new ToolService();
