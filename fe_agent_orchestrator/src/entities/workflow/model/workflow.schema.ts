import { z } from "zod";
import type { WorkspaceId } from "@/entities/workspace";
import type {
  CreateWorkflowInput,
  EdgeId,
  NodeId,
  UpdateWorkflowInput,
  Workflow,
  WorkflowEdge,
  WorkflowGraph,
  WorkflowId,
  WorkflowNode,
  WorkflowSummary,
} from "./workflow.types";

const workflowIdSchema = z
  .string()
  .min(1)
  .transform((s) => s as WorkflowId);
const workspaceIdSchema = z
  .string()
  .min(1)
  .transform((s) => s as WorkspaceId);

export const workflowStatusSchema = z.enum(["draft", "published", "archived"]);

const workflowSummaryWireSchema = z.object({
  id: workflowIdSchema,
  workspace_id: workspaceIdSchema,
  name: z.string(),
  slug: z.string(),
  description: z.string().nullable().optional(),
  status: workflowStatusSchema,
  created_by: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export function toWorkflowSummary(w: z.infer<typeof workflowSummaryWireSchema>): WorkflowSummary {
  return {
    id: w.id,
    workspaceId: w.workspace_id,
    name: w.name,
    slug: w.slug,
    description: w.description ?? undefined,
    status: w.status,
    createdBy: w.created_by ?? undefined,
    createdAt: w.created_at,
    updatedAt: w.updated_at,
  };
}

// ──────────────────────────────────────────────────────────────────
// Graph
// ──────────────────────────────────────────────────────────────────

const nodeTypeSchema = z.enum(["start", "agent", "tool", "condition", "end"]);
const edgeConditionSchema = z.object({
  kind: z.enum(["always", "equals", "expr"]),
  // Pydantic emits `null` for unset Optional fields; tolerate both shapes.
  path: z.string().nullable().optional(),
  value: z.unknown().optional(),
  expr: z.string().nullable().optional(),
});

const nodeWireSchema = z.object({
  id: z.string(),
  type: nodeTypeSchema,
  position: z.object({ x: z.number(), y: z.number() }),
  data: z.looseObject({
    label: z.string().optional().default(""),
    type: nodeTypeSchema.optional(),
    config: z.record(z.string(), z.unknown()).optional().default({}),
  }),
});

const edgeWireSchema = z.object({
  id: z.string(),
  source: z.string(),
  target: z.string(),
  label: z.string().nullable().optional(),
  condition: edgeConditionSchema.nullable().optional(),
});

const graphWireSchema = z.object({
  nodes: z.array(nodeWireSchema),
  edges: z.array(edgeWireSchema),
  viewport: z.object({ x: z.number(), y: z.number(), zoom: z.number() }).nullable().optional(),
});

function toWorkflowNode(n: z.infer<typeof nodeWireSchema>): WorkflowNode {
  return {
    id: n.id as NodeId,
    type: n.type,
    position: n.position,
    data: {
      label: n.data.label ?? n.id,
      type: n.data.type ?? n.type,
      config: n.data.config ?? {},
    },
  };
}

function toWorkflowEdge(e: z.infer<typeof edgeWireSchema>): WorkflowEdge {
  return {
    id: e.id as EdgeId,
    source: e.source as NodeId,
    target: e.target as NodeId,
    label: e.label ?? undefined,
    // Normalize Pydantic-style `null` → `undefined` so the typed condition
    // stays a clean optional everywhere downstream.
    condition: e.condition
      ? {
          kind: e.condition.kind,
          path: e.condition.path ?? undefined,
          value: e.condition.value,
          expr: e.condition.expr ?? undefined,
        }
      : undefined,
  };
}

export function toWorkflowGraph(g: z.infer<typeof graphWireSchema>): WorkflowGraph {
  return {
    nodes: g.nodes.map(toWorkflowNode),
    edges: g.edges.map(toWorkflowEdge),
    viewport: g.viewport ?? undefined,
  };
}

export function toWorkflowGraphWire(g: WorkflowGraph): z.infer<typeof graphWireSchema> {
  return {
    nodes: g.nodes.map((n) => ({
      id: n.id,
      type: n.type,
      position: n.position,
      data: { label: n.data.label, type: n.data.type, config: n.data.config },
    })),
    edges: g.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      condition: e.condition,
    })),
    viewport: g.viewport,
  };
}

// ──────────────────────────────────────────────────────────────────
// Workflow detail
// ──────────────────────────────────────────────────────────────────

const workflowDetailWireSchema = z.object({
  id: workflowIdSchema,
  workspace_id: workspaceIdSchema,
  name: z.string(),
  slug: z.string(),
  description: z.string().nullable().optional(),
  status: workflowStatusSchema,
  graph: graphWireSchema,
  compiled_graph: z.record(z.string(), z.unknown()),
  settings: z.record(z.string(), z.unknown()),
  created_by: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export function toWorkflow(w: z.infer<typeof workflowDetailWireSchema>): Workflow {
  return {
    id: w.id,
    workspaceId: w.workspace_id,
    name: w.name,
    slug: w.slug,
    description: w.description ?? undefined,
    status: w.status,
    graph: toWorkflowGraph(w.graph),
    compiledGraph: w.compiled_graph,
    settings: w.settings,
    createdBy: w.created_by ?? undefined,
    createdAt: w.created_at,
    updatedAt: w.updated_at,
  };
}

// ──────────────────────────────────────────────────────────────────
// Request body builders
// ──────────────────────────────────────────────────────────────────

export function toCreateWorkflowBody(input: CreateWorkflowInput): Record<string, unknown> {
  return {
    name: input.name,
    description: input.description,
    graph: input.graph ? toWorkflowGraphWire(input.graph) : undefined,
    settings: input.settings,
  };
}

export function toUpdateWorkflowBody(input: UpdateWorkflowInput): Record<string, unknown> {
  const body: Record<string, unknown> = {};
  if (input.name !== undefined) body.name = input.name;
  if (input.description !== undefined) body.description = input.description;
  if (input.status !== undefined) body.status = input.status;
  if (input.settings !== undefined) body.settings = input.settings;
  return body;
}

export { workflowSummaryWireSchema, workflowDetailWireSchema, graphWireSchema };
