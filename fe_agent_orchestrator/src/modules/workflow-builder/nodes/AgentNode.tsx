import type { NodeProps } from "reactflow";
import type { WorkflowNodeData } from "@/entities/workflow";
import { BaseNode } from "./BaseNode";

export function AgentNode(props: NodeProps<WorkflowNodeData>) {
  return <BaseNode {...props} accent="bg-violet-400" />;
}
