import type { Brand } from "@/shared/types/brand";
import type { WorkflowId } from "@/entities/workflow";
import type { WorkspaceId } from "@/entities/workspace";

export type RunId = Brand<string, "RunId">;

export type RunStatus = "queued" | "running" | "waiting" | "completed" | "failed" | "cancelled";
export type TriggerType = "manual" | "schedule" | "channel" | "api" | "test";
export type RunNodeStatus =
  | "queued"
  | "running"
  | "waiting"
  | "completed"
  | "failed"
  | "skipped"
  | "cancelled";

/** Light shape from `GET /workspaces/{ws}/runs/`. */
export type RunSummary = {
  id: RunId;
  workspaceId: WorkspaceId;
  workflowId?: WorkflowId;
  status: RunStatus;
  triggerType: TriggerType;
  triggerSource?: string;
  errorMessage?: string;
  totalInputTokens: number;
  totalOutputTokens: number;
  totalCostUsd: number;
  startedAt?: string;
  completedAt?: string;
  createdAt: string;
  updatedAt: string;
};

/** Per-step row. `output` is the merged delta this step contributed to run state. */
export type RunNode = {
  id: string;
  nodeId: string;
  nodeType: string;
  nodeLabel?: string;
  agentId?: string;
  toolId?: string;
  status: RunNodeStatus;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  errorMessage?: string;
  errorDetails: Record<string, unknown>;
  startedAt?: string;
  completedAt?: string;
};

/**
 * Persisted row from the runtime event stream (DB-backed `runtime_events`).
 *
 * Named `RunEventRow` to disambiguate from the realtime WebSocket
 * `RunEvent` discriminated union in ``run-event.types.ts`` (that one is the
 * live stream shape; this one is the historical DB shape).
 */
export type RunEventRow = {
  id: string;
  sequenceNumber: number;
  eventType: string;
  nodeId?: string;
  agentId?: string;
  toolId?: string;
  message?: string;
  payload: Record<string, unknown>;
  createdAt: string;
};

export type RunDetail = RunSummary & {
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  nodes: RunNode[];
  events: RunEventRow[];
};
