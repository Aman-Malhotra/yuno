import type { Brand } from "@/shared/types/brand";
import type { WorkspaceId } from "@/entities/workspace";

export type ToolId = Brand<string, "ToolId">;

export type ToolType = "builtin" | "http" | "messaging" | "agent_handoff" | "webhook" | "python" | "mock";

export type ToolStatus = "draft" | "active" | "disabled" | "archived";

/** Light shape from GET /workspaces/{ws}/tools/ */
export type ToolSummary = {
  id: ToolId;
  name: string;
  slug: string;
  description: string;
  type: ToolType;
  category: string;
  icon?: string;
  status: ToolStatus;
  version: number;
  createdAt: string;
  updatedAt: string;
};

/** Full shape from GET /workspaces/{ws}/tools/{id} */
export type ToolDetail = {
  id: ToolId;
  workspaceId?: WorkspaceId; // null for global built-ins
  name: string;
  slug: string;
  description: string;
  type: ToolType;
  category: string;
  icon?: string;
  status: ToolStatus;
  version: number;
  inputSchema: Record<string, unknown>;
  outputSchema: Record<string, unknown>;
  config: Record<string, unknown>;
  auth: Record<string, unknown>;
  guardrails: Record<string, unknown>;
  executionPolicy: Record<string, unknown>;
  channels: Record<string, unknown>;
  createdBy?: string;
  createdAt: string;
  updatedAt: string;
};

/** Body for POST /workspaces/{ws}/tools/ — minimal subset the v1 form surfaces. */
export type CreateToolInput = {
  name: string;
  description: string;
  type: ToolType;
  category?: string;
  icon?: string;
  inputSchema?: Record<string, unknown>;
  outputSchema?: Record<string, unknown>;
  config?: Record<string, unknown>;
  status?: ToolStatus;
};

/**
 * Body for PATCH /workspaces/{ws}/tools/{id} — every field optional. Per the
 * spec, `type` cannot be patched and `additionalProperties: false`, so we only
 * send keys the user actually changed.
 */
export type UpdateToolInput = {
  name?: string;
  description?: string;
  category?: string;
  icon?: string;
  inputSchema?: Record<string, unknown>;
  outputSchema?: Record<string, unknown>;
  config?: Record<string, unknown>;
  status?: ToolStatus;
  publishNewVersion?: boolean;
};

/** GET /workspaces/{ws}/tools/{id}/versions */
export type ToolVersionSummary = {
  id: string;
  toolId: ToolId;
  versionNumber: number;
  name: string;
  type: ToolType;
  createdAt: string;
  createdBy?: string;
};
