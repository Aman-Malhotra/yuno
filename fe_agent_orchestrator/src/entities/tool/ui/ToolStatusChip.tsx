import { Chip } from "@/shared/ui";
import type { ToolStatus } from "../model/tool.types";

const tones: Record<ToolStatus, "ok" | "warn" | "default" | "err"> = {
  active: "ok",
  draft: "warn",
  disabled: "err",
  archived: "default",
};

export function ToolStatusChip({ status }: { status: ToolStatus }) {
  return <Chip tone={tones[status]}>{status}</Chip>;
}
