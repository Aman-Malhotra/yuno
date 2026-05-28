import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  CircleSlash,
  Clock,
  Loader2,
  Play,
  Square,
  XCircle,
} from "lucide-react";

import {
  type RunDetail,
  type RunNodeStatus,
  type RunStatus,
  useCancelRun,
  useCreateTestRun,
  useRun,
} from "@/entities/run";
import type { WorkflowId } from "@/entities/workflow";
import type { WorkspaceId } from "@/entities/workspace";
import { cn } from "@/shared/lib/cn";

import { useWorkflowBuilderStore } from "../model/workflow-builder.store";

type Props = {
  workspaceId: WorkspaceId;
  workflowId: WorkflowId;
};

/**
 * Right-panel "Test Run" tab. Fires a manual run with caller-edited
 * initial state, then polls the run detail every second so the canvas
 * can paint per-node status rings and the panel can stream events.
 */
export function TestRunPanel({ workspaceId, workflowId }: Props) {
  const activeTestRunId = useWorkflowBuilderStore((s) => s.activeTestRunId);
  const setActiveTestRun = useWorkflowBuilderStore((s) => s.setActiveTestRun);
  const setStatuses = useWorkflowBuilderStore((s) => s.setTestRunNodeStatuses);

  const [inputJson, setInputJson] = useState<string>(() =>
    JSON.stringify(
      { message: "hello", channel: "manual", chat_id: 0 },
      null,
      2,
    ),
  );
  const [jsonError, setJsonError] = useState<string | null>(null);

  const createMut = useCreateTestRun(workspaceId, workflowId);
  const cancelMut = useCancelRun(workspaceId);

  // The useRun wrapper only accepts a plain number / false interval, so
  // we track the "should keep polling" flag locally and flip it off
  // when the run reaches a terminal state. One extra poll fires before
  // the flip lands — fine for a sub-second cadence.
  const [keepPolling, setKeepPolling] = useState(true);
  const run = useRun(workspaceId, activeTestRunId ?? undefined, {
    refetchInterval: keepPolling ? 1000 : false,
  });

  useEffect(() => {
    if (run.data && isTerminal(run.data.status)) setKeepPolling(false);
  }, [run.data]);

  // Whenever a new active run is set, resume polling.
  useEffect(() => {
    if (activeTestRunId) setKeepPolling(true);
  }, [activeTestRunId]);

  // Push status map into the store so canvas nodes can render rings.
  useEffect(() => {
    if (!run.data) return;
    const map: Record<string, RunNodeStatus> = {};
    for (const n of run.data.nodes) map[n.nodeId] = n.status;
    setStatuses(map);
  }, [run.data, setStatuses]);

  // Clear status map when the panel unmounts so an old run doesn't
  // bleed colour into a different workflow.
  useEffect(() => {
    return () => setStatuses({});
  }, [setStatuses]);

  const onRun = () => {
    let input: Record<string, unknown> = {};
    try {
      input = inputJson.trim() ? JSON.parse(inputJson) : {};
      if (typeof input !== "object" || input === null || Array.isArray(input)) {
        throw new Error("input must be a JSON object");
      }
    } catch (err) {
      setJsonError(err instanceof Error ? err.message : "invalid JSON");
      return;
    }
    setJsonError(null);
    createMut.mutate(input, {
      onSuccess: (summary) => {
        setActiveTestRun(summary.id);
      },
    });
  };

  const onStop = () => {
    if (activeTestRunId) cancelMut.mutate(activeTestRunId);
  };

  const isRunning = run.data ? !isTerminal(run.data.status) : createMut.isPending;

  return (
    <div className="flex h-full min-h-0 flex-col bg-canvas-panel">
      {/* Input editor */}
      <div className="border-b border-canvas-rule p-3">
        <label className="mb-1 flex items-center justify-between text-[10px] uppercase tracking-eyebrow text-ink-faint">
          <span>Initial state (JSON)</span>
          {jsonError && <span className="text-signal-err normal-case">{jsonError}</span>}
        </label>
        <textarea
          value={inputJson}
          onChange={(e) => {
            setInputJson(e.target.value);
            if (jsonError) setJsonError(null);
          }}
          rows={6}
          spellCheck={false}
          className={cn(
            "block w-full resize-y rounded-sm border bg-canvas-inset px-2 py-1.5 font-mono text-[11px] text-ink",
            "focus:border-sodium focus:outline-none",
            jsonError ? "border-signal-err/60" : "border-canvas-rule",
          )}
        />
        <div className="mt-2 flex gap-2">
          <button
            type="button"
            onClick={onRun}
            disabled={createMut.isPending || isRunning}
            className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-sm border border-sodium/50 bg-sodium/10 px-3 py-1.5 text-[12px] text-sodium hover:bg-sodium/20 disabled:opacity-40"
          >
            {createMut.isPending ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <Play size={12} />
            )}
            {isRunning ? "Running…" : "Run"}
          </button>
          {isRunning && (
            <button
              type="button"
              onClick={onStop}
              disabled={cancelMut.isPending}
              className="inline-flex items-center gap-1.5 rounded-sm border border-canvas-rule bg-canvas-inset px-3 py-1.5 text-[12px] text-ink-mute hover:bg-canvas-panel hover:text-ink disabled:opacity-40"
              title="Cancel run"
            >
              <Square size={12} />
            </button>
          )}
        </div>
        {createMut.error && (
          <p className="mt-2 text-[11px] text-signal-err">{createMut.error.message}</p>
        )}
      </div>

      {/* Run header */}
      {run.data && (
        <div className="border-b border-canvas-rule px-3 py-2">
          <div className="flex items-center gap-2">
            <RunStatusChip status={run.data.status} />
            <code className="truncate font-mono text-[10px] text-ink-mute" title={run.data.id}>
              {run.data.id.slice(0, 8)}…
            </code>
          </div>
          {run.data.errorMessage && (
            <p className="mt-1.5 break-words text-[11px] text-signal-err">{run.data.errorMessage}</p>
          )}
        </div>
      )}

      {/* Event feed */}
      <EventFeed run={run.data ?? null} />
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────── */

function isTerminal(status: RunStatus): boolean {
  return status === "completed" || status === "failed" || status === "cancelled";
}


function EventFeed({ run }: { run: RunDetail | null }) {
  // Auto-scroll to bottom when new events arrive (typical chat-log behavior).
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const events = useMemo(() => run?.events ?? [], [run?.events]);

  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [events.length]);

  if (!run) {
    return (
      <div className="flex flex-1 items-center justify-center px-4 py-8 text-center text-[11px] text-ink-mute">
        Trigger a run to see live events.
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center px-4 py-8 text-center text-[11px] text-ink-mute">
        Waiting for events…
      </div>
    );
  }

  return (
    <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-3 py-2">
      <ul className="space-y-1">
        {events.map((e) => (
          <li
            key={e.id}
            className="rounded-sm border border-canvas-rule bg-canvas-inset px-2 py-1.5 text-[10px]"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-ink">{e.eventType}</span>
              {e.nodeId && (
                <code className="truncate font-mono text-ink-mute">{e.nodeId}</code>
              )}
            </div>
            {e.message && (
              <p className="mt-0.5 truncate text-[10px] text-ink-dim" title={e.message}>
                {e.message}
              </p>
            )}
            <p className="mt-0.5 font-mono text-[9px] text-ink-faint">{e.createdAt}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

function RunStatusChip({ status }: { status: RunStatus }) {
  const { icon, label, cls } = STATUS_META[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 text-[10px] uppercase tracking-eyebrow",
        cls,
      )}
    >
      {icon}
      {label}
    </span>
  );
}

const STATUS_META: Record<
  RunStatus,
  { icon: React.ReactNode; label: string; cls: string }
> = {
  queued: {
    icon: <Clock size={10} />,
    label: "queued",
    cls: "border-canvas-rule bg-canvas-inset text-ink-mute",
  },
  running: {
    icon: <Loader2 size={10} className="animate-spin" />,
    label: "running",
    cls: "border-sodium/40 bg-sodium/10 text-sodium",
  },
  waiting: {
    icon: <Clock size={10} />,
    label: "waiting",
    cls: "border-canvas-rule bg-canvas-inset text-ink-mute",
  },
  completed: {
    icon: <CheckCircle2 size={10} />,
    label: "completed",
    cls: "border-signal-ok/40 bg-signal-ok/10 text-signal-ok",
  },
  failed: {
    icon: <XCircle size={10} />,
    label: "failed",
    cls: "border-signal-err/40 bg-signal-err/10 text-signal-err",
  },
  cancelled: {
    icon: <CircleSlash size={10} />,
    label: "cancelled",
    cls: "border-canvas-rule bg-canvas-inset text-ink-mute",
  },
};

// Re-export AlertCircle so unused-import linting doesn't trip if we trim
// the chip later — quiet TS without changing runtime behaviour.
export const _unused = AlertCircle;
