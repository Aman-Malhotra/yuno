---
title: Node Registry Pattern
impact: CRITICAL
impactDescription: Without a single registry, adding a new node type touches the palette, canvas, inspector, validation, and persistence — easy to miss one
tags: workflow-builder, registry, node-types
---

## Node Registry Pattern

Define every node type **once** in a registry. Component, config schema, default data, and graph constraints live together.

### Node type union

```ts
// entities/workflow/model/workflow-node.types.ts
export type WorkflowNodeType =
  | "start"
  | "agent"
  | "tool"
  | "condition"
  | "router"
  | "parallel"
  | "human_approval"
  | "delay"
  | "webhook"
  | "end";

export type WorkflowNodeData = {
  label: string;
  type: WorkflowNodeType;
  config: Record<string, unknown>;
  validationErrors?: string[];
};
```

### Node definition

```ts
// modules/workflow-builder/model/node-registry.ts
import type { ComponentType } from "react";
import type { NodeProps } from "reactflow";
import type { ZodSchema } from "zod";
import type { WorkflowNodeType, WorkflowNodeData } from "@/entities/workflow";

import { StartNode } from "../nodes/StartNode";
import { AgentNode } from "../nodes/AgentNode";
import { ToolNode } from "../nodes/ToolNode";
// ...

export type NodeDefinition = {
  type: WorkflowNodeType;
  label: string;
  description: string;
  icon: string;                    // lucide-react icon name
  canHaveIncoming: boolean;
  canHaveOutgoing: boolean;
  maxIncoming?: number;
  maxOutgoing?: number;
  defaultData: () => WorkflowNodeData;
  configSchema: ZodSchema;
  component: ComponentType<NodeProps<WorkflowNodeData>>;
};

export const nodeRegistry: Record<WorkflowNodeType, NodeDefinition> = {
  start: {
    type: "start",
    label: "Start",
    description: "Entry point of the workflow",
    icon: "play",
    canHaveIncoming: false,
    canHaveOutgoing: true,
    maxOutgoing: 1,
    defaultData: () => ({ label: "Start", type: "start", config: {} }),
    configSchema: startNodeConfigSchema,
    component: StartNode,
  },
  agent: {
    type: "agent",
    label: "Agent",
    description: "Run an agent step",
    icon: "bot",
    canHaveIncoming: true,
    canHaveOutgoing: true,
    defaultData: () => ({
      label: "Agent",
      type: "agent",
      config: { agentId: null, input: "" },
    }),
    configSchema: agentNodeConfigSchema,
    component: AgentNode,
  },
  tool: {
    type: "tool",
    label: "Tool",
    description: "Execute a registered tool",
    icon: "wrench",
    canHaveIncoming: true,
    canHaveOutgoing: true,
    defaultData: () => ({
      label: "Tool",
      type: "tool",
      config: { toolId: null, input: {} },
    }),
    configSchema: toolNodeConfigSchema,
    component: ToolNode,
  },
  condition: {
    type: "condition",
    label: "Condition",
    description: "Branch on a boolean expression",
    icon: "git-branch",
    canHaveIncoming: true,
    canHaveOutgoing: true,
    maxOutgoing: 2,
    defaultData: () => ({
      label: "Condition",
      type: "condition",
      config: { expression: "" },
    }),
    configSchema: conditionNodeConfigSchema,
    component: ConditionNode,
  },
  // ... router, parallel, human_approval, delay, webhook, end
};
```

### Drive every UI piece from the registry

```tsx
// Node palette
{Object.values(nodeRegistry).map((def) => (
  <PaletteItem key={def.type} icon={def.icon} label={def.label} type={def.type} />
))}

// Inspector
const def = nodeRegistry[selectedNode.data.type];
return <ConfigForm schema={def.configSchema} value={selectedNode.data.config} />;

// React Flow nodeTypes
const nodeTypes = Object.fromEntries(
  Object.entries(nodeRegistry).map(([type, def]) => [type, def.component]),
);
```

### Adding a new node type — single checklist

1. Add the string literal to `WorkflowNodeType`
2. Add a file in `modules/workflow-builder/nodes/`
3. Add the Zod config schema
4. Add the entry to `nodeRegistry`
5. Add any validation-specific rules in `lib/graph-validation.ts` ([[workflow-builder-validation]])

That's it — palette, canvas, inspector pick it up automatically.

See: [[workflow-builder-canvas]], [[workflow-builder-validation]]
