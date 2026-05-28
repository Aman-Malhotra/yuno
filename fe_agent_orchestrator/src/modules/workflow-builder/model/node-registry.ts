import type { ComponentType } from "react";
import type { NodeProps } from "reactflow";
import { z, type ZodType } from "zod";

import type { WorkflowNodeData, WorkflowNodeType } from "@/entities/workflow";

import { StartNode } from "../nodes/StartNode";
import { AgentNode } from "../nodes/AgentNode";
import { ToolNode } from "../nodes/ToolNode";
import { ConditionNode } from "../nodes/ConditionNode";
import { EndNode } from "../nodes/EndNode";

export type NodeDefinition = {
  type: WorkflowNodeType;
  label: string;
  description: string;
  icon: string;
  canHaveIncoming: boolean;
  canHaveOutgoing: boolean;
  defaultData: () => WorkflowNodeData;
  configSchema: ZodType;
  component: ComponentType<NodeProps<WorkflowNodeData>>;
};

const emptyConfig = z.object({});

export const nodeRegistry: Partial<Record<WorkflowNodeType, NodeDefinition>> = {
  start: {
    type: "start",
    label: "Start",
    description: "Entry point of the workflow",
    icon: "play",
    canHaveIncoming: false,
    canHaveOutgoing: true,
    defaultData: () => ({ label: "Start", type: "start", config: {} }),
    configSchema: emptyConfig,
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
    configSchema: z.object({
      agentId: z.string().nullable(),
      input: z.string().optional(),
    }),
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
    configSchema: z.object({
      toolId: z.string().nullable(),
      input: z.record(z.string(), z.unknown()).optional(),
    }),
    component: ToolNode,
  },
  condition: {
    type: "condition",
    label: "Condition",
    description: "Branch on a boolean expression",
    icon: "git-branch",
    canHaveIncoming: true,
    canHaveOutgoing: true,
    defaultData: () => ({
      label: "Condition",
      type: "condition",
      config: { expression: "" },
    }),
    configSchema: z.object({ expression: z.string() }),
    component: ConditionNode,
  },
  end: {
    type: "end",
    label: "End",
    description: "Terminates the workflow",
    icon: "circle-stop",
    canHaveIncoming: true,
    canHaveOutgoing: false,
    defaultData: () => ({ label: "End", type: "end", config: {} }),
    configSchema: emptyConfig,
    component: EndNode,
  },
};
