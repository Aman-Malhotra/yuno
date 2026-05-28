import type { NodeProps } from "reactflow";
import type { WorkflowNodeData } from "@/entities/workflow";
import { BaseNode } from "./BaseNode";

export function ConditionNode(props: NodeProps<WorkflowNodeData>) {
  return <BaseNode {...props} accent="bg-sky-400" />;
}
