import { z } from "zod";

import type { WorkflowId } from "@/entities/workflow";
import type { WorkspaceId } from "@/entities/workspace";

import type {
  RunDetail,
  RunEventRow,
  RunId,
  RunNode,
  RunSummary,
} from "./run.types";

const runIdSchema = z
  .string()
  .min(1)
  .transform((s) => s as RunId);
const workspaceIdSchema = z
  .string()
  .min(1)
  .transform((s) => s as WorkspaceId);
const workflowIdSchema = z
  .string()
  .min(1)
  .transform((s) => s as WorkflowId);

export const runStatusSchema = z.enum([
  "queued",
  "running",
  "waiting",
  "completed",
  "failed",
  "cancelled",
]);
export const triggerTypeSchema = z.enum(["manual", "schedule", "channel", "api", "test"]);
export const runNodeStatusSchema = z.enum([
  "queued",
  "running",
  "waiting",
  "completed",
  "failed",
  "skipped",
  "cancelled",
]);

const numericish = z.union([z.number(), z.string().transform((s) => Number(s))]);

export const runSummaryWireSchema = z.object({
  id: runIdSchema,
  workspace_id: workspaceIdSchema,
  workflow_id: workflowIdSchema.nullable().optional(),
  status: runStatusSchema,
  trigger_type: triggerTypeSchema,
  trigger_source: z.string().nullable().optional(),
  error_message: z.string().nullable().optional(),
  total_input_tokens: z.number(),
  total_output_tokens: z.number(),
  total_cost_usd: numericish,
  started_at: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const runNodeWireSchema = z.object({
  id: z.string(),
  node_id: z.string(),
  node_type: z.string(),
  node_label: z.string().nullable().optional(),
  agent_id: z.string().nullable().optional(),
  tool_id: z.string().nullable().optional(),
  status: runNodeStatusSchema,
  input: z.record(z.string(), z.unknown()),
  output: z.record(z.string(), z.unknown()),
  error_message: z.string().nullable().optional(),
  error_details: z.record(z.string(), z.unknown()),
  started_at: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional(),
});

export const runEventWireSchema = z.object({
  id: z.string(),
  sequence_number: z.number(),
  event_type: z.string(),
  node_id: z.string().nullable().optional(),
  agent_id: z.string().nullable().optional(),
  tool_id: z.string().nullable().optional(),
  message: z.string().nullable().optional(),
  payload: z.record(z.string(), z.unknown()),
  created_at: z.string(),
});

export const runDetailWireSchema = runSummaryWireSchema.extend({
  input: z.record(z.string(), z.unknown()),
  output: z.record(z.string(), z.unknown()),
  nodes: z.array(runNodeWireSchema),
  events: z.array(runEventWireSchema),
});

export function toRunSummary(r: z.infer<typeof runSummaryWireSchema>): RunSummary {
  return {
    id: r.id,
    workspaceId: r.workspace_id,
    workflowId: r.workflow_id ?? undefined,
    status: r.status,
    triggerType: r.trigger_type,
    triggerSource: r.trigger_source ?? undefined,
    errorMessage: r.error_message ?? undefined,
    totalInputTokens: r.total_input_tokens,
    totalOutputTokens: r.total_output_tokens,
    totalCostUsd: r.total_cost_usd,
    startedAt: r.started_at ?? undefined,
    completedAt: r.completed_at ?? undefined,
    createdAt: r.created_at,
    updatedAt: r.updated_at,
  };
}

export function toRunNode(n: z.infer<typeof runNodeWireSchema>): RunNode {
  return {
    id: n.id,
    nodeId: n.node_id,
    nodeType: n.node_type,
    nodeLabel: n.node_label ?? undefined,
    agentId: n.agent_id ?? undefined,
    toolId: n.tool_id ?? undefined,
    status: n.status,
    input: n.input,
    output: n.output,
    errorMessage: n.error_message ?? undefined,
    errorDetails: n.error_details,
    startedAt: n.started_at ?? undefined,
    completedAt: n.completed_at ?? undefined,
  };
}

export function toRunEvent(e: z.infer<typeof runEventWireSchema>): RunEventRow {
  return {
    id: e.id,
    sequenceNumber: e.sequence_number,
    eventType: e.event_type,
    nodeId: e.node_id ?? undefined,
    agentId: e.agent_id ?? undefined,
    toolId: e.tool_id ?? undefined,
    message: e.message ?? undefined,
    payload: e.payload,
    createdAt: e.created_at,
  };
}

export function toRunDetail(r: z.infer<typeof runDetailWireSchema>): RunDetail {
  return {
    ...toRunSummary(r),
    input: r.input,
    output: r.output,
    nodes: r.nodes.map(toRunNode),
    events: r.events.map(toRunEvent),
  };
}
