---
title: Local UI State in Zustand
impact: CRITICAL
impactDescription: Lifting selection/panel state to React Context re-renders the whole canvas on every node click
tags: state, zustand, ui-state
---

## Local UI State in Zustand

Zustand owns transient UI state that does not need to survive a refresh. Per-module store, co-located in `model/`.

### What belongs in Zustand

- selected node id / selected edge id
- which inspector panel is open
- canvas zoom mode (`pan` / `select` / `connect`)
- active tab in the agent editor
- unsaved workflow draft (until saved to backend)
- run timeline cursor / paused state
- playground chat scroll lock

### What does NOT belong in Zustand

- backend data → [[state-server-tanstack-query]]
- form values → [[state-form-rhf-zod]]
- ephemeral component state (input focus, hover) → `useState`

### Standard store shape

```ts
// modules/workflow-builder/model/workflow-builder.store.ts
import { create } from "zustand";
import type { NodeId, EdgeId } from "@/entities/workflow";

export type WorkflowBuilderState = {
  selectedNodeId: NodeId | null;
  selectedEdgeId: EdgeId | null;
  isInspectorOpen: boolean;
  canvasMode: "pan" | "select" | "connect";

  selectNode: (id: NodeId | null) => void;
  selectEdge: (id: EdgeId | null) => void;
  openInspector: () => void;
  closeInspector: () => void;
  setCanvasMode: (m: WorkflowBuilderState["canvasMode"]) => void;
};

export const useWorkflowBuilderStore = create<WorkflowBuilderState>((set) => ({
  selectedNodeId: null,
  selectedEdgeId: null,
  isInspectorOpen: false,
  canvasMode: "select",

  selectNode: (id) => set({ selectedNodeId: id, isInspectorOpen: id !== null }),
  selectEdge: (id) => set({ selectedEdgeId: id }),
  openInspector: () => set({ isInspectorOpen: true }),
  closeInspector: () => set({ isInspectorOpen: false }),
  setCanvasMode: (canvasMode) => set({ canvasMode }),
}));
```

### Use selectors to avoid re-renders

```ts
// ✅ Only re-renders when selectedNodeId changes
const selectedNodeId = useWorkflowBuilderStore((s) => s.selectedNodeId);

// ❌ Re-renders on every state change
const { selectedNodeId } = useWorkflowBuilderStore();
```

### One store per module, not one global store

Each module gets its own store file. Cross-module shared UI state is rare — when it exists, lift it to `app/` providers, not a global Zustand store.

See: [[state-server-tanstack-query]], [[workflow-builder-canvas]]
