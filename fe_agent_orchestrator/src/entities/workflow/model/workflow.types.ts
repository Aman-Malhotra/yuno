import type { Brand } from "@/shared/types/brand";
import type { WorkspaceId } from "@/entities/workspace";

export type WorkflowId = Brand<string, "WorkflowId">;
export type NodeId = Brand<string, "NodeId">;
export type EdgeId = Brand<string, "EdgeId">;

export type WorkflowStatus = "draft" | "published" | "archived";

/** Light shape from list endpoints — no graph_json. */
export type WorkflowSummary = {
  id: WorkflowId;
  workspaceId: WorkspaceId;
  name: string;
  slug: string;
  description?: string;
  status: WorkflowStatus;
  createdBy?: string;
  createdAt: string;
  updatedAt: string;
};

export type WorkflowNodeType = "start" | "agent" | "tool" | "condition" | "end";

export type WorkflowNodeData = {
  label: string;
  type: WorkflowNodeType;
  config: Record<string, unknown>;
};

export type WorkflowNode = {
  id: NodeId;
  type: WorkflowNodeType;
  position: { x: number; y: number };
  data: WorkflowNodeData;
};

/**
 * Edge predicate. Mirrors the backend `WorkflowEdgeCondition`.
 *
 * - `always`  — unconditional (default when omitted)
 * - `equals`  — `state[path] === value`
 * - `expr`    — safe DSL expression evaluated on the run state
 *
 * Multiple conditional edges sharing a source compile to langgraph's
 * `add_conditional_edges` on the backend.
 */
export type WorkflowEdgeConditionKind = "always" | "equals" | "expr";
export type WorkflowEdgeCondition = {
  kind: WorkflowEdgeConditionKind;
  path?: string;
  value?: unknown;
  expr?: string;
};

export type WorkflowEdge = {
  id: EdgeId;
  source: NodeId;
  target: NodeId;
  label?: string;
  condition?: WorkflowEdgeCondition;
};

/** Raw React Flow graph — the editor's source of truth. */
export type WorkflowGraph = {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  viewport?: { x: number; y: number; zoom: number };
};

/** Full workflow with graph payload — fetched lazily on the builder page. */
export type Workflow = {
  id: WorkflowId;
  workspaceId: WorkspaceId;
  name: string;
  slug: string;
  description?: string;
  status: WorkflowStatus;
  graph: WorkflowGraph;
  /** Server-derived, langgraph-ready normalization of `graph`. Read-only. */
  compiledGraph: Record<string, unknown>;
  settings: Record<string, unknown>;
  createdBy?: string;
  createdAt: string;
  updatedAt: string;
};

/** Form payload mirroring CreateWorkflowRequest in the spec. */
export type CreateWorkflowInput = {
  name: string;
  description?: string;
  graph?: WorkflowGraph;
  settings?: Record<string, unknown>;
};

/** Partial-update payload for metadata. The graph is updated via `updateGraph`. */
export type UpdateWorkflowInput = {
  name?: string;
  description?: string;
  status?: WorkflowStatus;
  settings?: Record<string, unknown>;
};
