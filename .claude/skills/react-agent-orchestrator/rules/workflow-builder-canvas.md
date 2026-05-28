---
title: Workflow Builder Canvas with React Flow
impact: CRITICAL
impactDescription: The visual workflow builder is the product's defining feature — the canvas decision shapes 80% of the frontend
tags: workflow-builder, react-flow, canvas
---

## Workflow Builder Canvas with React Flow

Use [React Flow / xyflow](https://reactflow.dev) for the canvas. Client-side only. No SSR.

### Module layout

```txt
modules/workflow-builder/
  ui/
    WorkflowBuilderPage.tsx       # composes everything
    WorkflowCanvas.tsx            # <ReactFlow /> wrapper
    WorkflowToolbar.tsx           # save, publish, run, undo
    WorkflowInspector.tsx         # right panel: node/edge config
    WorkflowMinimap.tsx
    WorkflowNodePalette.tsx       # left panel: drag-to-add
  nodes/                          # one file per node type
    StartNode.tsx
    AgentNode.tsx
    ToolNode.tsx
    ConditionNode.tsx
    RouterNode.tsx
    ParallelNode.tsx
    HumanApprovalNode.tsx
    DelayNode.tsx
    WebhookNode.tsx
    EndNode.tsx
  edges/
    WorkflowEdge.tsx              # default edge styling
    ConditionalEdge.tsx           # labeled true/false branches
  model/
    workflow-builder.store.ts
    node-registry.ts
    edge-registry.ts
  lib/
    node-factory.ts               # create a fresh node with defaults
    edge-factory.ts
    graph-validation.ts           # pure (see workflow-builder-validation)
    layout-workflow.ts            # auto-layout (e.g. dagre)
  config/
    workflow-builder.config.ts
  index.ts
```

### Canvas component

```tsx
// modules/workflow-builder/ui/WorkflowCanvas.tsx
"use client"; // only relevant if you ever move to Next.js

import { useCallback } from "react";
import ReactFlow, {
  Background, Controls, MiniMap,
  type Edge, type Node, type Connection,
  useEdgesState, useNodesState, addEdge,
} from "reactflow";
import "reactflow/dist/style.css";

import { nodeRegistry } from "../model/node-registry";
import { edgeRegistry } from "../model/edge-registry";
import { useWorkflowBuilderStore } from "../model/workflow-builder.store";

const nodeTypes = Object.fromEntries(
  Object.entries(nodeRegistry).map(([type, def]) => [type, def.component]),
);

const edgeTypes = Object.fromEntries(
  Object.entries(edgeRegistry).map(([type, def]) => [type, def.component]),
);

export function WorkflowCanvas({
  initialNodes,
  initialEdges,
}: {
  initialNodes: Node[];
  initialEdges: Edge[];
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const selectNode = useWorkflowBuilderStore((s) => s.selectNode);

  const onConnect = useCallback(
    (c: Connection) => setEdges((eds) => addEdge({ ...c, type: "workflow" }, eds)),
    [setEdges],
  );

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      onNodeClick={(_, n) => selectNode(n.id)}
      onPaneClick={() => selectNode(null)}
      fitView
    >
      <Background />
      <Controls />
      <MiniMap />
    </ReactFlow>
  );
}
```

### Rules

- Canvas state (`nodes`, `edges`) is owned by React Flow's `useNodesState`/`useEdgesState` while editing
- Selection / panel state lives in the Zustand store ([[state-local-zustand]])
- Saved workflows persist via TanStack Query mutations ([[state-server-tanstack-query]])
- Never put the canvas inside a server component
- Validate before publish ([[workflow-builder-validation]])
- Live run status overlays come from a separate stream that maps `runEvent.nodeId → status` and merges visually — does not mutate the canvas data

See: [[workflow-builder-node-registry]], [[workflow-builder-validation]], [[state-local-zustand]]
