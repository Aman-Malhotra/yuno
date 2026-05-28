import type { DragEvent } from "react";

import type { WorkflowNodeType } from "@/entities/workflow";

import { nodeRegistry } from "../model/node-registry";

export const PALETTE_DATA_TYPE = "application/x-yuno-node-type";
/** Side channel used when the dragged tile is a workspace agent — carries the agent id. */
export const PALETTE_AGENT_REF = "application/x-yuno-agent-ref";

export type PaletteDropPayload =
  | { kind: "node-type"; type: WorkflowNodeType }
  | { kind: "agent"; agentId: string; name: string };

export function getPaletteDropPayload(event: DragEvent): PaletteDropPayload | null {
  const agentRaw = event.dataTransfer.getData(PALETTE_AGENT_REF);
  if (agentRaw) {
    try {
      const parsed = JSON.parse(agentRaw) as { agentId: string; name: string };
      if (parsed.agentId) return { kind: "agent", agentId: parsed.agentId, name: parsed.name };
    } catch {
      // fall through
    }
  }
  const typeRaw = event.dataTransfer.getData(PALETTE_DATA_TYPE);
  if (typeRaw && typeRaw in nodeRegistry) {
    return { kind: "node-type", type: typeRaw as WorkflowNodeType };
  }
  return null;
}
