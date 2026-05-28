import { useCallback, useMemo, type DragEvent } from "react";
import { Bot } from "lucide-react";
import { useReactFlow } from "reactflow";

import { useAgentsInWorkspace, type AgentSummary, type AgentId } from "@/entities/agent";
import type { NodeId, WorkflowNodeType } from "@/entities/workflow";
import type { WorkspaceId } from "@/entities/workspace";
import { cn } from "@/shared/lib/cn";

import { PALETTE_AGENT_REF, PALETTE_DATA_TYPE } from "../lib/palette-drag";
import { nodeRegistry } from "../model/node-registry";
import { useWorkflowBuilderStore } from "../model/workflow-builder.store";

type Props = { workspaceId: WorkspaceId };

const FOCUS_ZOOM = 1.15;
const FOCUS_DURATION_MS = 400;

/**
 * Two-section palette:
 *   1. Generic node types (start/agent/tool/condition/end) — drop one to add
 *      an unconfigured node and finish configuring it in the inspector.
 *   2. Workspace agents — *drag* one to spawn an `agent` node with its
 *      `agentId` pre-wired; *click* one that already exists on the canvas
 *      to recenter the viewport on it and open the inspector.
 */
export function WorkflowNodePalette({ workspaceId }: Props) {
  const { setCenter, getNode } = useReactFlow();
  const nodes = useWorkflowBuilderStore((s) => s.nodes);
  const selectedNodeId = useWorkflowBuilderStore((s) => s.selectedNodeId);
  const selectNode = useWorkflowBuilderStore((s) => s.selectNode);

  // Map of agent_id → canvas node id, so the click handler can decide
  // between "focus existing" and "no-op" in one hop without re-scanning
  // the nodes list inside the callback.
  const agentNodeByAgentId = useMemo(() => {
    const map = new Map<string, string>();
    for (const n of nodes) {
      if (n.type !== "agent") continue;
      const id = (n.data?.config as { agentId?: string | null } | undefined)?.agentId;
      if (id) map.set(id, n.id);
    }
    return map;
  }, [nodes]);

  const onNodeTypeDragStart = useCallback((event: DragEvent<HTMLLIElement>, type: WorkflowNodeType) => {
    event.dataTransfer.setData(PALETTE_DATA_TYPE, type);
    event.dataTransfer.effectAllowed = "move";
  }, []);

  const onAgentDragStart = useCallback((event: DragEvent<HTMLLIElement>, agent: AgentSummary) => {
    event.dataTransfer.setData(PALETTE_AGENT_REF, JSON.stringify({ agentId: agent.id, name: agent.name }));
    event.dataTransfer.effectAllowed = "move";
  }, []);

  const focusAgent = useCallback(
    (agentId: AgentId) => {
      const nodeId = agentNodeByAgentId.get(agentId);
      if (!nodeId) return;
      const node = getNode(nodeId);
      if (!node) return;
      // `setCenter` takes a flow-space point — aim at the node's center
      // (its `position` is top-left). Fall back to ~node size when
      // dimensions haven't landed yet (first frame after mount).
      const w = node.width ?? 180;
      const h = node.height ?? 60;
      setCenter(node.position.x + w / 2, node.position.y + h / 2, {
        zoom: FOCUS_ZOOM,
        duration: FOCUS_DURATION_MS,
      });
      selectNode(nodeId as NodeId);
    },
    [agentNodeByAgentId, getNode, setCenter, selectNode],
  );

  const agents = useAgentsInWorkspace(workspaceId);

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-canvas-rule bg-canvas-panel">
      <section className="border-b border-canvas-rule p-3">
        <h2 className="mb-2 text-[10px] font-semibold uppercase tracking-eyebrow text-ink-mute">Nodes</h2>
        <ul className="flex flex-col gap-1">
          {Object.values(nodeRegistry).map((def) => (
            <li
              key={def!.type}
              draggable
              onDragStart={(e) => onNodeTypeDragStart(e, def!.type)}
              className="cursor-grab rounded-md border border-canvas-rule bg-canvas px-2.5 py-1.5 text-xs text-ink-dim hover:border-sodium hover:text-ink"
            >
              <div className="font-medium">{def!.label}</div>
              <div className="text-[10px] text-ink-mute">{def!.description}</div>
            </li>
          ))}
        </ul>
      </section>

      <section className="flex min-h-0 flex-1 flex-col p-3">
        <h2 className="mb-2 text-[10px] font-semibold uppercase tracking-eyebrow text-ink-mute">Agents</h2>
        {agents.isPending && <p className="text-[11px] text-ink-mute">Loading…</p>}
        {agents.data?.items.length === 0 && (
          <p className="text-[11px] text-ink-mute">No agents in this workspace yet. Create one to wire it in.</p>
        )}
        <ul className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto pr-1">
          {(agents.data?.items ?? []).map((agent) => {
            const placedNodeId = agentNodeByAgentId.get(agent.id);
            const isOnCanvas = Boolean(placedNodeId);
            const isSelected = placedNodeId !== undefined && placedNodeId === selectedNodeId;
            return (
              <li
                key={agent.id}
                draggable
                onDragStart={(e) => onAgentDragStart(e, agent)}
                onClick={() => {
                  if (isOnCanvas) focusAgent(agent.id);
                }}
                title={
                  isOnCanvas
                    ? "Click to focus on this agent · drag to add another instance"
                    : "Drag onto the canvas to add this agent"
                }
                className={cn(
                  "flex items-start gap-2 rounded-md border bg-canvas px-2.5 py-1.5 text-xs text-ink-dim",
                  isOnCanvas ? "cursor-pointer" : "cursor-grab",
                  isSelected
                    ? "border-sodium text-ink ring-1 ring-sodium/40"
                    : "border-canvas-rule hover:border-sodium hover:text-ink",
                )}
              >
                <span className="mt-0.5 inline-flex h-4 w-4 items-center justify-center rounded-sm bg-sodium-tint text-sodium">
                  <Bot size={10} strokeWidth={1.8} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate font-medium">{agent.name}</span>
                    {isOnCanvas && (
                      <span className="shrink-0 rounded-sm bg-sodium-tint px-1 text-[9px] font-semibold uppercase tracking-eyebrow text-sodium">
                        on canvas
                      </span>
                    )}
                  </div>
                  {agent.description && <div className="line-clamp-2 text-[10px] text-ink-mute">{agent.description}</div>}
                </div>
              </li>
            );
          })}
        </ul>
      </section>
    </aside>
  );
}
