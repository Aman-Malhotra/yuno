import type { NodeProps } from "reactflow";
import type { WorkflowNodeData } from "@/entities/workflow";
import { BaseNode } from "./BaseNode";

export function ToolNode(props: NodeProps<WorkflowNodeData>) {
  return <BaseNode {...props} accent="bg-amber-400" />;
}
