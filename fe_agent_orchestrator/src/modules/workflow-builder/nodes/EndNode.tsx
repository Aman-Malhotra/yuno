import type { NodeProps } from "reactflow";
import type { WorkflowNodeData } from "@/entities/workflow";
import { BaseNode } from "./BaseNode";

export function EndNode(props: NodeProps<WorkflowNodeData>) {
  return <BaseNode {...props} accent="bg-rose-400" showSource={false} />;
}
