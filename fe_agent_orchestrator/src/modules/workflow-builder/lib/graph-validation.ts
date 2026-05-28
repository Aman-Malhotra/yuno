import type { WorkflowGraph, WorkflowNode, WorkflowEdge } from "@/entities/workflow";

export type WorkflowValidationError = {
  level: "error" | "warning";
  scope: "graph" | "node" | "edge";
  nodeId?: string;
  edgeId?: string;
  code: string;
  message: string;
};

export type WorkflowValidationResult = {
  ok: boolean;
  errors: WorkflowValidationError[];
};

export function validateWorkflow(draft: WorkflowGraph): WorkflowValidationResult {
  const errors: WorkflowValidationError[] = [];

  const starts = draft.nodes.filter((n) => n.type === "start");
  if (starts.length === 0) {
    errors.push({
      level: "error",
      scope: "graph",
      code: "MISSING_START",
      message: "Workflow must have a start node",
    });
  } else if (starts.length > 1) {
    errors.push({
      level: "error",
      scope: "graph",
      code: "MULTIPLE_START",
      message: "Workflow has multiple start nodes",
    });
  }

  if (draft.nodes.every((n) => n.type !== "end")) {
    errors.push({
      level: "error",
      scope: "graph",
      code: "MISSING_END",
      message: "Workflow must have at least one end node",
    });
  }

  errors.push(...checkOrphanNodes(draft.nodes, draft.edges));
  errors.push(...checkAgentNodes(draft.nodes));
  errors.push(...checkEdgesIntoStart(draft.nodes, draft.edges));

  return { ok: errors.every((e) => e.level !== "error"), errors };
}

function checkOrphanNodes(nodes: WorkflowNode[], edges: WorkflowEdge[]): WorkflowValidationError[] {
  const connected = new Set<string>();
  edges.forEach((e) => {
    connected.add(e.source);
    connected.add(e.target);
  });
  return nodes
    .filter((n) => !connected.has(n.id) && nodes.length > 1)
    .map((n) => ({
      level: "warning" as const,
      scope: "node" as const,
      nodeId: n.id,
      code: "ORPHAN_NODE",
      message: `Node "${n.data.label}" is not connected`,
    }));
}

function checkAgentNodes(nodes: WorkflowNode[]): WorkflowValidationError[] {
  return nodes
    .filter((n) => n.type === "agent" && !n.data.config["agentId"])
    .map((n) => ({
      level: "error" as const,
      scope: "node" as const,
      nodeId: n.id,
      code: "AGENT_NODE_MISSING_AGENT",
      message: "Agent node must reference an agent",
    }));
}

function checkEdgesIntoStart(nodes: WorkflowNode[], edges: WorkflowEdge[]): WorkflowValidationError[] {
  const startIds = new Set(nodes.filter((n) => n.type === "start").map((n) => n.id));
  return edges
    .filter((e) => startIds.has(e.target))
    .map((e) => ({
      level: "error" as const,
      scope: "edge" as const,
      edgeId: e.id,
      code: "EDGE_INTO_START",
      message: "Start node cannot have incoming edges",
    }));
}
