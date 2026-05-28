import { create } from "zustand";
import {
  addEdge as rfAddEdge,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
} from "reactflow";

import type { RunId, RunNodeStatus } from "@/entities/run";
import type {
  EdgeId,
  NodeId,
  WorkflowEdge,
  WorkflowEdgeCondition,
  WorkflowGraph,
  WorkflowNodeData,
  WorkflowNodeType,
} from "@/entities/workflow";

export type SaveStatus = "idle" | "dirty" | "saving" | "saved" | "error";

/**
 * Live status map for the active test run, keyed by GRAPH node id (the
 * stable string id like ``"router"`` from the saved graph — NOT React
 * Flow's instance id). The test-run panel polls run detail every second
 * and pushes statuses here; each node renderer reads its own status to
 * paint a coloured ring on the canvas. Empty map = no active run.
 */
export type TestRunNodeStatusMap = Record<string, RunNodeStatus>;

export type WorkflowBuilderState = {
  // ── Graph state ────────────────────────────────────────────────────
  nodes: Node<WorkflowNodeData>[];
  edges: Edge<WorkflowEdgeData>[];

  // ── Selection / inspector ─────────────────────────────────────────
  selectedNodeId: NodeId | null;
  selectedEdgeId: EdgeId | null;
  isInspectorOpen: boolean;

  // ── Save lifecycle ────────────────────────────────────────────────
  saveStatus: SaveStatus;
  lastSavedAt: string | null;
  saveError: string | null;
  /** Monotonic counter — increments on any graph mutation. Callers debounce on this. */
  graphRevision: number;

  // ── Right panel + test run ────────────────────────────────────────
  rightPanelTab: "inspector" | "test_run";
  activeTestRunId: RunId | null;
  testRunNodeStatuses: TestRunNodeStatusMap;

  // ── Actions: graph mutation (drive autosave) ──────────────────────
  setGraph: (graph: WorkflowGraph) => void;
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: Connection) => void;
  addNode: (input: {
    type: WorkflowNodeType;
    position: { x: number; y: number };
    data?: Partial<WorkflowNodeData>;
  }) => void;
  updateNodeData: (
    nodeId: NodeId,
    patch: Partial<WorkflowNodeData> | ((d: WorkflowNodeData) => WorkflowNodeData),
  ) => void;
  updateEdgeCondition: (edgeId: EdgeId, condition: WorkflowEdgeCondition | undefined) => void;
  removeNode: (nodeId: NodeId) => void;
  removeEdge: (edgeId: EdgeId) => void;

  // ── Actions: selection ────────────────────────────────────────────
  selectNode: (id: NodeId | null) => void;
  selectEdge: (id: EdgeId | null) => void;
  openInspector: () => void;
  closeInspector: () => void;

  // ── Actions: save lifecycle ───────────────────────────────────────
  markSaving: () => void;
  markSaved: () => void;
  markError: (message: string) => void;

  // ── Actions: test run ─────────────────────────────────────────────
  setRightPanelTab: (tab: "inspector" | "test_run") => void;
  setActiveTestRun: (runId: RunId | null) => void;
  setTestRunNodeStatuses: (statuses: TestRunNodeStatusMap) => void;

  // ── Pure read helpers ─────────────────────────────────────────────
  toWorkflowGraph: () => WorkflowGraph;
};

/**
 * Edge `data` payload — we keep the typed condition on the React Flow edge
 * itself so the canvas can render label/condition badges without a
 * round-trip through our typed adapter on every render.
 */
export type WorkflowEdgeData = {
  condition?: WorkflowEdgeCondition;
};

function genId(prefix: string): string {
  // Short, sortable-ish id; collision-resistant enough for an unsaved canvas.
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

function bumpDirty(state: WorkflowBuilderState): Partial<WorkflowBuilderState> {
  return {
    graphRevision: state.graphRevision + 1,
    saveStatus: state.saveStatus === "saving" ? "saving" : "dirty",
    saveError: null,
  };
}

export const useWorkflowBuilderStore = create<WorkflowBuilderState>((set, get) => ({
  nodes: [],
  edges: [],

  selectedNodeId: null,
  selectedEdgeId: null,
  isInspectorOpen: false,

  saveStatus: "idle",
  lastSavedAt: null,
  saveError: null,
  graphRevision: 0,

  rightPanelTab: "inspector",
  activeTestRunId: null,
  testRunNodeStatuses: {},

  setGraph: (graph) =>
    set({
      nodes: graph.nodes.map((n) => ({
        id: n.id,
        type: n.type,
        position: n.position,
        data: n.data,
      })),
      edges: graph.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        data: { condition: e.condition },
      })),
      // Loading from server is the new clean baseline — reset dirty flag
      // so the autosave effect doesn't immediately re-PATCH.
      saveStatus: "idle",
      graphRevision: 0,
      saveError: null,
    }),

  onNodesChange: (changes) =>
    set((state) => {
      const next = applyNodeChanges(changes, state.nodes) as Node<WorkflowNodeData>[];
      // Position-only drag events are noisy; only count *committed* drags
      // (`dragging: false` arrives once on mouseup) as autosave-worthy.
      const meaningful = changes.some(
        (c) => c.type === "add" || c.type === "remove" || (c.type === "position" && c.dragging === false),
      );
      return {
        nodes: next,
        ...(meaningful ? bumpDirty(state) : {}),
      };
    }),

  onEdgesChange: (changes) =>
    set((state) => {
      const next = applyEdgeChanges(changes, state.edges) as Edge<WorkflowEdgeData>[];
      const meaningful = changes.some((c) => c.type === "add" || c.type === "remove");
      return {
        edges: next,
        ...(meaningful ? bumpDirty(state) : {}),
      };
    }),

  onConnect: (connection) =>
    set((state) => {
      if (!connection.source || !connection.target) return state;
      // Block edges into a start node — same invariant the server enforces.
      const target = state.nodes.find((n) => n.id === connection.target);
      if (target?.type === "start") return state;
      const id = genId("e");
      const newEdge: Edge<WorkflowEdgeData> = {
        id,
        source: connection.source,
        target: connection.target,
        data: { condition: { kind: "always" } },
      };
      return {
        edges: rfAddEdge(newEdge, state.edges) as Edge<WorkflowEdgeData>[],
        ...bumpDirty(state),
      };
    }),

  addNode: ({ type, position, data }) =>
    set((state) => {
      const id = genId("n");
      const node: Node<WorkflowNodeData> = {
        id,
        type,
        position,
        data: {
          label: data?.label ?? defaultLabel(type),
          type,
          config: data?.config ?? defaultConfig(type),
        },
      };
      return {
        nodes: [...state.nodes, node],
        ...bumpDirty(state),
      };
    }),

  updateNodeData: (nodeId, patch) =>
    set((state) => ({
      nodes: state.nodes.map((n) => {
        if (n.id !== nodeId) return n;
        const nextData = typeof patch === "function" ? patch(n.data) : { ...n.data, ...patch };
        return { ...n, data: nextData };
      }),
      ...bumpDirty(state),
    })),

  updateEdgeCondition: (edgeId, condition) =>
    set((state) => ({
      edges: state.edges.map((e) => (e.id === edgeId ? { ...e, data: { ...e.data, condition } } : e)),
      ...bumpDirty(state),
    })),

  removeNode: (nodeId) =>
    set((state) => ({
      nodes: state.nodes.filter((n) => n.id !== nodeId),
      edges: state.edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
      selectedNodeId: state.selectedNodeId === nodeId ? null : state.selectedNodeId,
      ...bumpDirty(state),
    })),

  removeEdge: (edgeId) =>
    set((state) => ({
      edges: state.edges.filter((e) => e.id !== edgeId),
      selectedEdgeId: state.selectedEdgeId === edgeId ? null : state.selectedEdgeId,
      ...bumpDirty(state),
    })),

  // React Flow draws the selection outline from `node.selected` / `edge.selected`
  // — clicks through `onNodeClick` flip that via `onNodesChange`, but a
  // programmatic select (e.g. palette → focus) has to set it explicitly.
  selectNode: (id) =>
    set((state) => ({
      selectedNodeId: id,
      selectedEdgeId: null,
      isInspectorOpen: id !== null,
      nodes: state.nodes.map((n) => (n.selected === (n.id === id) ? n : { ...n, selected: n.id === id })),
      edges: state.edges.map((e) => (e.selected ? { ...e, selected: false } : e)),
    })),
  selectEdge: (id) =>
    set((state) => ({
      selectedEdgeId: id,
      selectedNodeId: null,
      isInspectorOpen: id !== null,
      edges: state.edges.map((e) => (e.selected === (e.id === id) ? e : { ...e, selected: e.id === id })),
      nodes: state.nodes.map((n) => (n.selected ? { ...n, selected: false } : n)),
    })),
  openInspector: () => set({ isInspectorOpen: true }),
  closeInspector: () => set({ isInspectorOpen: false }),

  markSaving: () => set({ saveStatus: "saving" }),
  markSaved: () =>
    set((state) => ({
      // Only flip to `saved` if no further mutations landed during the round-trip.
      saveStatus: state.saveStatus === "saving" ? "saved" : state.saveStatus,
      lastSavedAt: new Date().toISOString(),
      saveError: null,
    })),
  markError: (message) => set({ saveStatus: "error", saveError: message }),

  setRightPanelTab: (tab) => set({ rightPanelTab: tab }),
  setActiveTestRun: (runId) => set({ activeTestRunId: runId, testRunNodeStatuses: {} }),
  setTestRunNodeStatuses: (statuses) => set({ testRunNodeStatuses: statuses }),

  toWorkflowGraph: () => {
    const state = get();
    return {
      nodes: state.nodes.map((n) => ({
        id: n.id as NodeId,
        type: n.type as WorkflowNodeType,
        position: n.position,
        data: n.data,
      })),
      edges: state.edges.map<WorkflowEdge>((e) => ({
        id: e.id as EdgeId,
        source: e.source as NodeId,
        target: e.target as NodeId,
        label: typeof e.label === "string" ? e.label : undefined,
        condition: e.data?.condition,
      })),
    };
  },
}));

function defaultLabel(type: WorkflowNodeType): string {
  switch (type) {
    case "start":
      return "Start";
    case "end":
      return "End";
    case "agent":
      return "Agent";
    case "tool":
      return "Tool";
    case "condition":
      return "Condition";
  }
}

function defaultConfig(type: WorkflowNodeType): Record<string, unknown> {
  switch (type) {
    case "agent":
      return { agentId: null, input: "" };
    case "tool":
      return { toolId: null, input: {} };
    case "condition":
      return { expression: "" };
    default:
      return {};
  }
}
