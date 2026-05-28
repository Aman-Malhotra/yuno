import { Chip } from "@/shared/ui";
import type { WorkflowStatus } from "../model/workflow.types";

const toneByStatus: Record<WorkflowStatus, "ok" | "warn" | "default"> = {
  published: "ok",
  draft: "warn",
  archived: "default",
};

export function WorkflowStatusChip({ status }: { status: WorkflowStatus }) {
  return <Chip tone={toneByStatus[status]}>{status}</Chip>;
}
