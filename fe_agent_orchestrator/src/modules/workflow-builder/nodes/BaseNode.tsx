import { Handle, Position, type NodeProps } from "reactflow";

import type { RunNodeStatus } from "@/entities/run";
import { cn } from "@/shared/lib/cn";
import type { WorkflowNodeData } from "@/entities/workflow";

import { useWorkflowBuilderStore } from "../model/workflow-builder.store";

type BaseNodeProps = NodeProps<WorkflowNodeData> & {
  accent: string;
  showTarget?: boolean;
  showSource?: boolean;
};

/** Per-status outer styling. Each entry is the wrapping class applied to
 * the node when the active test run has that node in this state. Selected
 * (manual click) still wins — the violet outline takes precedence. */
const STATUS_CLASS: Record<RunNodeStatus, { ring: string; dot: string }> = {
  queued: { ring: "ring-2 ring-ink-mute/40", dot: "bg-ink-mute" },
  running: {
    ring: "ring-2 ring-sodium animate-pulse shadow-[0_0_18px_rgba(198,137,34,0.45)]",
    dot: "bg-sodium",
  },
  waiting: { ring: "ring-2 ring-ink-mute/40", dot: "bg-ink-mute" },
  completed: { ring: "ring-2 ring-signal-ok/60", dot: "bg-signal-ok" },
  failed: { ring: "ring-2 ring-signal-err shadow-[0_0_18px_rgba(220,38,38,0.45)]", dot: "bg-signal-err" },
  skipped: { ring: "ring-2 ring-ink-faint/40", dot: "bg-ink-faint" },
  cancelled: { ring: "ring-2 ring-ink-mute/40", dot: "bg-ink-mute" },
};

export function BaseNode({ id, data, selected, accent, showTarget = true, showSource = true }: BaseNodeProps) {
  // Live status during a test run. Read by id so each node only re-renders
  // when its own status changes (zustand returns referentially-stable
  // strings → React bails out cleanly on no-op updates).
  const runStatus = useWorkflowBuilderStore((s) => s.testRunNodeStatuses[id]);
  const statusStyle = runStatus ? STATUS_CLASS[runStatus] : undefined;

  return (
    <div
      className={cn(
        "min-w-[180px] rounded-lg border bg-canvas-panel px-3 py-2 shadow-md transition-shadow",
        selected ? "border-violet-500" : "border-canvas-border",
        statusStyle?.ring,
      )}
    >
      {showTarget && <Handle type="target" position={Position.Top} className="!bg-zinc-500" />}
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "h-2 w-2 rounded-full",
            // Status colour overrides the static accent during a run so
            // the audience can tell which node is live at a glance.
            statusStyle ? statusStyle.dot : accent,
          )}
        />
        <span className="text-[10px] font-medium uppercase tracking-wide text-zinc-500">{data.type}</span>
        {runStatus && (
          <span className="ml-auto text-[9px] font-mono uppercase tracking-eyebrow text-ink-mute">
            {runStatus}
          </span>
        )}
      </div>
      <div className="mt-1 text-sm font-semibold text-ink">{data.label}</div>
      {showSource && <Handle type="source" position={Position.Bottom} className="!bg-zinc-500" />}
    </div>
  );
}
