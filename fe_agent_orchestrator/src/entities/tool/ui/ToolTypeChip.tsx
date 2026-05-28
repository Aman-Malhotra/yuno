import { Chip } from "@/shared/ui";
import type { ToolType } from "../model/tool.types";

const labels: Record<ToolType, string> = {
  builtin: "built-in",
  http: "http",
  messaging: "messaging",
  agent_handoff: "handoff",
  webhook: "webhook",
  python: "python",
  mock: "mock",
};

const tones: Record<ToolType, "default" | "accent" | "ok" | "warn"> = {
  builtin: "default",
  http: "accent",
  messaging: "accent",
  agent_handoff: "accent",
  webhook: "accent",
  python: "warn",
  mock: "default",
};

export function ToolTypeChip({ type }: { type: ToolType }) {
  return <Chip tone={tones[type]}>{labels[type]}</Chip>;
}
