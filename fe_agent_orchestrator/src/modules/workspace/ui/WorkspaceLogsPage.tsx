import { useMemo, useState } from "react";
import { Link, useParams, useSearch } from "@tanstack/react-router";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Copy,
  ExternalLink,
  GitBranch,
  Check as Tick,
  Loader2,
  Trash2,
  XCircle,
  XOctagon,
} from "lucide-react";

import { useAgent } from "@/entities/agent";
import {
  useCancelRun,
  useDeleteRun,
  useRun,
  useRuns,
  type RunDetail,
  type RunEventRow,
  type RunId,
  type RunNode,
  type RunNodeStatus,
  type RunStatus,
  type RunSummary,
} from "@/entities/run";
import { useTool } from "@/entities/tool";
import { useWorkflowsInWorkspace, type WorkflowId, type WorkflowSummary } from "@/entities/workflow";
import type { WorkspaceId } from "@/entities/workspace";
import { cn } from "@/shared/lib/cn";
import { Chip, Field, SectionHeader, Select } from "@/shared/ui";

const STATUS_OPTIONS: { value: "" | RunStatus; label: string }[] = [
  { value: "", label: "All statuses" },
  { value: "queued", label: "Queued" },
  { value: "running", label: "Running" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
  { value: "cancelled", label: "Cancelled" },
];

export function WorkspaceLogsPage() {
  const { workspaceId } = useParams({ from: "/protected/workspaces/$workspaceId" });
  const wsId = workspaceId as WorkspaceId;
  // Deep-link support: settings → logs button passes `?workflowId=...` to
  // pre-apply the filter. We seed local state from it on first mount; the
  // dropdown can still override it after that.
  const search = useSearch({ from: "/protected/workspaces/$workspaceId/logs" });

  const [workflowId, setWorkflowId] = useState<WorkflowId | undefined>(
    () => (search.workflowId as WorkflowId | undefined) ?? undefined,
  );
  const [statusFilter, setStatusFilter] = useState<RunStatus | undefined>(undefined);
  const [selectedRunId, setSelectedRunId] = useState<RunId | null>(null);

  const workflows = useWorkflowsInWorkspace(wsId, 1, 100);
  const runs = useRuns(wsId, {
    workflowId,
    status: statusFilter,
    pageSize: 50,
    // Light auto-refresh on the list so newly-queued runs show up without a manual reload.
    refetchInterval: 5000,
  });
  const selectedRun = useRun(wsId, selectedRunId ?? undefined, {
    // Tighter refresh on a live run; React Query will dedupe identical results.
    refetchInterval: 2000,
  });

  const workflowsById = useMemo(() => {
    const map = new Map<string, WorkflowSummary>();
    (workflows.data?.items ?? []).forEach((w) => map.set(w.id, w));
    return map;
  }, [workflows.data?.items]);

  return (
    <div className="mx-auto w-full max-w-[1400px] px-6 py-8">
      <SectionHeader
        title="Logs"
        meta="Per-run timeline, per-step IO, token + cost roll-up."
        right={runs.data ? <Chip tone="default">{runs.data.total} runs</Chip> : null}
      />

      <div className="hairline-x mt-6" />

      <div className="mt-6 flex flex-wrap items-end gap-3">
        <div className="min-w-[260px] flex-1">
          <Field label="Workflow">
            <Select
              value={workflowId ?? ""}
              options={[
                { value: "", label: "All workflows" },
                ...(workflows.data?.items ?? []).map((w) => ({ value: w.id, label: w.name })),
              ]}
              onChange={(e) => {
                setWorkflowId((e.target.value || undefined) as WorkflowId | undefined);
                setSelectedRunId(null);
              }}
            />
          </Field>
        </div>
        <div className="min-w-[180px]">
          <Field label="Status">
            <Select
              value={statusFilter ?? ""}
              options={STATUS_OPTIONS}
              onChange={(e) => {
                setStatusFilter((e.target.value || undefined) as RunStatus | undefined);
                setSelectedRunId(null);
              }}
            />
          </Field>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-[360px_minmax(0,1fr)]">
        <RunList
          runs={runs.data?.items ?? []}
          isPending={runs.isPending}
          error={runs.error}
          workflowsById={workflowsById}
          selectedRunId={selectedRunId}
          workspaceId={wsId}
          onSelect={(id) => setSelectedRunId(id)}
          onDeleted={(id) => {
            if (id === selectedRunId) setSelectedRunId(null);
          }}
        />

        <RunDetailPanel
          workspaceId={wsId}
          run={selectedRun.data ?? null}
          isPending={selectedRun.isPending && Boolean(selectedRunId)}
          error={selectedRun.error}
          workflowName={selectedRun.data?.workflowId ? workflowsById.get(selectedRun.data.workflowId)?.name : undefined}
          onDeleted={() => setSelectedRunId(null)}
        />
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Run list (left column)
// ──────────────────────────────────────────────────────────────────────

function RunList({
  runs,
  isPending,
  error,
  workflowsById,
  selectedRunId,
  workspaceId,
  onSelect,
  onDeleted,
}: {
  runs: RunSummary[];
  isPending: boolean;
  error: Error | null;
  workflowsById: Map<string, WorkflowSummary>;
  selectedRunId: RunId | null;
  workspaceId: WorkspaceId;
  onSelect: (id: RunId) => void;
  onDeleted: (id: RunId) => void;
}) {
  if (error) {
    return (
      <div className="rounded-md border border-signal-err/40 bg-signal-err/5 p-4 text-xs text-signal-err">
        {error.message}
      </div>
    );
  }
  if (isPending) {
    return (
      <div className="flex flex-col gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-16 animate-pulse rounded-md border border-canvas-rule bg-canvas-panel/60" />
        ))}
      </div>
    );
  }
  if (runs.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-canvas-rule bg-canvas-panel/40 p-6 text-center text-xs text-ink-mute">
        No runs match these filters.
      </div>
    );
  }
  return (
    <ul className="flex max-h-[calc(100vh-22rem)] flex-col gap-1.5 overflow-y-auto pr-1">
      {runs.map((run) => {
        const isSelected = run.id === selectedRunId;
        const wfName = run.workflowId ? workflowsById.get(run.workflowId)?.name : undefined;
        return (
          <li key={run.id}>
            {/* role=button keeps the whole row clickable while letting the
                nested cancel/delete <button>s capture clicks via stopPropagation. */}
            <div
              role="button"
              tabIndex={0}
              onClick={() => onSelect(run.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(run.id);
                }
              }}
              className={cn(
                "flex w-full cursor-pointer flex-col gap-1.5 rounded-md border bg-canvas-panel px-3 py-2.5 text-left transition-colors",
                isSelected ? "border-sodium ring-1 ring-sodium/40" : "border-canvas-rule hover:border-sodium/60",
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-xs font-medium text-ink">{wfName ?? "Unknown workflow"}</span>
                <div className="flex items-center gap-1.5">
                  <RunStatusChip status={run.status} />
                  <RunRowActions
                    workspaceId={workspaceId}
                    run={run}
                    onDeleted={() => onDeleted(run.id)}
                    compact
                  />
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-x-2.5 gap-y-0.5 text-[10px] text-ink-mute">
                <span className="font-mono">{run.id.slice(0, 8)}</span>
                <span>·</span>
                <span>{run.triggerType}</span>
                <span>·</span>
                <span title={run.createdAt}>{formatRelative(run.createdAt)}</span>
                {run.totalCostUsd > 0 && (
                  <>
                    <span>·</span>
                    <span>${run.totalCostUsd.toFixed(4)}</span>
                  </>
                )}
              </div>
              {run.errorMessage && <div className="line-clamp-1 text-[11px] text-signal-err">{run.errorMessage}</div>}
            </div>
          </li>
        );
      })}
    </ul>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Run detail (right column)
// ──────────────────────────────────────────────────────────────────────

function RunDetailPanel({
  workspaceId,
  run,
  isPending,
  error,
  workflowName,
  onDeleted,
}: {
  workspaceId: WorkspaceId;
  run: RunDetail | null;
  isPending: boolean;
  error: Error | null;
  workflowName?: string;
  onDeleted: () => void;
}) {
  if (error) {
    return (
      <div className="rounded-md border border-signal-err/40 bg-signal-err/5 p-4 text-xs text-signal-err">
        {error.message}
      </div>
    );
  }
  if (isPending) {
    return <div className="h-[480px] animate-pulse rounded-md border border-canvas-rule bg-canvas-panel/60" />;
  }
  if (!run) {
    return (
      <div className="grid place-items-center rounded-md border border-dashed border-canvas-rule bg-canvas-panel/40 p-12 text-xs text-ink-mute">
        Select a run on the left to inspect step-by-step output.
      </div>
    );
  }

  const toolCallCounts = countToolCalls(run.nodes, run.events);

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-col gap-2 rounded-md border border-canvas-rule bg-canvas-panel p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="truncate text-sm font-medium text-ink">{workflowName ?? "Run"}</span>
              {/* Deep-link to the workflow builder. Only renders when the run
                  still points at a live workflow row (deleted workflows leave
                  workflowId=null on the run). */}
              {run.workflowId && (
                <Link
                  to="/workspaces/$workspaceId/workflows/$workflowId"
                  params={{ workspaceId, workflowId: run.workflowId }}
                  title="Open workflow"
                  className="inline-flex items-center gap-1 rounded-md border border-canvas-rule px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-eyebrow text-ink-mute hover:border-sodium hover:text-sodium"
                >
                  <GitBranch size={10} strokeWidth={1.8} />
                  Open
                  <ExternalLink size={10} strokeWidth={1.8} />
                </Link>
              )}
            </div>
            <div className="font-mono text-[11px] text-ink-mute">{run.id}</div>
          </div>
          <div className="flex items-center gap-2">
            <RunStatusChip status={run.status} />
            <CopyRunButton run={run} />
            <RunRowActions workspaceId={workspaceId} run={run} onDeleted={onDeleted} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <MetricCell label="Trigger" value={run.triggerType} />
          <MetricCell label="Duration" value={formatDuration(run.startedAt, run.completedAt)} />
          <MetricCell label="Tokens (in / out)" value={`${run.totalInputTokens} / ${run.totalOutputTokens}`} />
          <MetricCell label="Cost" value={`$${run.totalCostUsd.toFixed(4)}`} />
        </div>
        {run.errorMessage && (
          <div className="rounded-md border border-signal-err/40 bg-signal-err/5 px-3 py-2 text-xs text-signal-err">
            {run.errorMessage}
          </div>
        )}
      </div>

      {/* Steps */}
      <div className="rounded-md border border-canvas-rule bg-canvas-panel">
        <header className="flex items-center justify-between border-b border-canvas-rule px-4 py-2">
          <span className="text-[10px] font-semibold uppercase tracking-eyebrow text-ink-mute">Steps</span>
          <span className="text-[11px] text-ink-mute">{run.nodes.length} total</span>
        </header>
        <ul className="flex flex-col">
          {run.nodes.length === 0 && (
            <li className="px-4 py-6 text-center text-xs text-ink-mute">No steps recorded yet.</li>
          )}
          {run.nodes.map((node) => (
            <StepRow
              key={node.id}
              node={node}
              workspaceId={workspaceId}
              // Pre-filter the event stream so each row only sees its own
              // events. Cheap on a 500-event cap; saves the row from doing
              // the filter inside its render path.
              events={run.events.filter((e) => e.nodeId === node.nodeId)}
            />
          ))}
        </ul>
      </div>

      {/* Tool call counts */}
      {toolCallCounts.length > 0 && (
        <div className="rounded-md border border-canvas-rule bg-canvas-panel">
          <header className="flex items-center justify-between border-b border-canvas-rule px-4 py-2">
            <span className="text-[10px] font-semibold uppercase tracking-eyebrow text-ink-mute">Tool calls</span>
            <span className="text-[11px] text-ink-mute">
              {toolCallCounts.length} tool{toolCallCounts.length === 1 ? "" : "s"}
            </span>
          </header>
          <ul className="flex flex-col divide-y divide-canvas-rule">
            {toolCallCounts.map((row) => (
              <ToolCallRow key={`${row.nodeId}:${row.toolId}`} workspaceId={workspaceId} row={row} />
            ))}
          </ul>
        </div>
      )}

      {/* Final state */}
      <CollapsibleJson label="Initial input" value={run.input} defaultOpen={false} />
      <CollapsibleJson label="Final state" value={run.output} defaultOpen={false} />
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Cancel + delete actions — shared between row + detail header
// ──────────────────────────────────────────────────────────────────────

const TERMINAL_STATUSES: Set<RunStatus> = new Set(["completed", "failed", "cancelled"]);

function RunRowActions({
  workspaceId,
  run,
  onDeleted,
  compact = false,
}: {
  workspaceId: WorkspaceId;
  run: RunSummary | RunDetail;
  onDeleted: () => void;
  compact?: boolean;
}) {
  const cancel = useCancelRun(workspaceId);
  const remove = useDeleteRun(workspaceId);
  const isTerminal = TERMINAL_STATUSES.has(run.status);
  const busy = cancel.isPending || remove.isPending;
  const size = compact ? 12 : 13;

  const stop = (e: React.MouseEvent) => {
    // Row uses role=button + onClick on the wrapper; stop the bubble so
    // clicking these icons doesn't also select the run.
    e.stopPropagation();
  };

  const onCancel = (e: React.MouseEvent) => {
    stop(e);
    if (!confirm(`Cancel run ${run.id.slice(0, 8)}? Any in-flight worker will be aborted.`)) return;
    cancel.mutate(run.id);
  };

  const onDelete = (e: React.MouseEvent) => {
    stop(e);
    if (!confirm(`Delete run ${run.id.slice(0, 8)}? This removes all steps and events.`)) return;
    remove.mutate(run.id, { onSuccess: () => onDeleted() });
  };

  return (
    <span className="inline-flex items-center gap-1" onClick={stop}>
      {!isTerminal && (
        <button
          type="button"
          onClick={onCancel}
          disabled={busy}
          aria-label="Cancel run"
          title="Cancel run"
          className={cn(
            "inline-flex items-center justify-center rounded-md border border-canvas-rule text-ink-mute",
            "hover:border-sodium hover:text-sodium disabled:opacity-50",
            compact ? "h-5 w-5" : "h-7 w-7",
          )}
        >
          <XOctagon size={size} strokeWidth={1.8} />
        </button>
      )}
      <button
        type="button"
        onClick={onDelete}
        disabled={busy}
        aria-label="Delete run"
        title="Delete run"
        className={cn(
          "inline-flex items-center justify-center rounded-md border border-canvas-rule text-ink-mute",
          "hover:border-signal-err hover:text-signal-err disabled:opacity-50",
          compact ? "h-5 w-5" : "h-7 w-7",
        )}
      >
        <Trash2 size={size} strokeWidth={1.8} />
      </button>
    </span>
  );
}

function MetricCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-md border border-canvas-rule bg-canvas px-2.5 py-1.5">
      <span className="text-[10px] uppercase tracking-eyebrow text-ink-mute">{label}</span>
      <span className="truncate text-xs font-medium text-ink">{value}</span>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Step row — collapsible, shows agent/tool ref + IO
// ──────────────────────────────────────────────────────────────────────

function StepRow({
  node,
  workspaceId,
  events,
}: {
  node: RunNode;
  workspaceId: WorkspaceId;
  events: RunEventRow[];
}) {
  const [open, setOpen] = useState(false);
  return (
    <li className="border-b border-canvas-rule last:border-b-0">
      <div
        role="button"
        tabIndex={0}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setOpen((o) => !o);
          }
        }}
        className="flex w-full cursor-pointer items-center justify-between gap-3 px-4 py-2.5 text-left hover:bg-canvas/40"
      >
        <div className="flex min-w-0 items-center gap-2">
          <NodeStatusIcon status={node.status} />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="truncate text-xs font-medium text-ink">{node.nodeLabel || node.nodeId}</span>
              <Chip tone="default">{node.nodeType}</Chip>
            </div>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] text-ink-mute">
              <span className="font-mono">{node.nodeId}</span>
              {node.startedAt && (
                <>
                  <span>·</span>
                  <span>{formatDuration(node.startedAt, node.completedAt)}</span>
                </>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Quick deep-link to the referenced entity — visible without expanding the row.
              stopPropagation so the toggle doesn't fire when the user clicks the link. */}
          {node.agentId && (
            <Link
              to="/workspaces/$workspaceId/agents/$agentId"
              params={{ workspaceId, agentId: node.agentId as never }}
              onClick={(e) => e.stopPropagation()}
              title="Open agent details"
              className="inline-flex items-center gap-1 rounded-md border border-canvas-rule px-2 py-0.5 text-[10px] font-medium uppercase tracking-eyebrow text-ink-mute hover:border-sodium hover:text-sodium"
            >
              Open agent
              <ExternalLink size={10} strokeWidth={1.8} />
            </Link>
          )}
          {node.toolId && (
            <Link
              to="/workspaces/$workspaceId/tools/$toolId"
              params={{ workspaceId, toolId: node.toolId as never }}
              onClick={(e) => e.stopPropagation()}
              title="Open tool details"
              className="inline-flex items-center gap-1 rounded-md border border-canvas-rule px-2 py-0.5 text-[10px] font-medium uppercase tracking-eyebrow text-ink-mute hover:border-sodium hover:text-sodium"
            >
              Open tool
              <ExternalLink size={10} strokeWidth={1.8} />
            </Link>
          )}
          <span className="text-[11px] text-ink-mute">{open ? "−" : "+"}</span>
        </div>
      </div>
      {open && (
        <div className="flex flex-col gap-2 border-t border-canvas-rule bg-canvas/30 px-4 py-3">
          {node.agentId && <AgentRefLine workspaceId={workspaceId} agentId={node.agentId} />}
          {node.toolId && <ToolRefLine workspaceId={workspaceId} toolId={node.toolId} />}
          {node.errorMessage && (
            <div className="rounded-md border border-signal-err/40 bg-signal-err/5 px-3 py-2 text-xs text-signal-err">
              {node.errorMessage}
            </div>
          )}
          <StepEventTimeline events={events} workspaceId={workspaceId} />
          <JsonBlock label="Input" value={node.input} />
          <JsonBlock label="Output" value={node.output} />
        </div>
      )}
    </li>
  );
}

/**
 * Per-step event timeline. Pairs ``tool.called`` with the matching
 * ``tool.result`` by ``sequence_number`` order and renders each pair as
 * one collapsible row: tool name, status, args, and result. Surfaces the
 * tool-call chain so a hop-limit failure no longer leaves the operator
 * wondering what the agent actually did.
 */
function StepEventTimeline({
  events,
  workspaceId,
}: {
  events: RunEventRow[];
  workspaceId: WorkspaceId;
}) {
  // Build (called, result?) pairs in sequence order. A "called" without a
  // matching "result" is rendered as in-flight (the agent never got to
  // process the response — usually because the next LLM call failed).
  const pairs = useMemo(() => {
    type Pair = { called: RunEventRow; result: RunEventRow | null };
    const out: Pair[] = [];
    let pending: RunEventRow | null = null;
    const sorted = [...events].sort((a, b) => a.sequenceNumber - b.sequenceNumber);
    for (const event of sorted) {
      if (event.eventType === "tool.called") {
        if (pending) out.push({ called: pending, result: null });
        pending = event;
      } else if (event.eventType === "tool.result" && pending) {
        out.push({ called: pending, result: event });
        pending = null;
      }
    }
    if (pending) out.push({ called: pending, result: null });
    return out;
  }, [events]);

  if (pairs.length === 0) return null;

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-eyebrow text-ink-mute">
          Tool calls · {pairs.length}
        </span>
      </div>
      <ol className="flex flex-col gap-1.5 rounded-md border border-canvas-rule bg-canvas px-2 py-2">
        {pairs.map((pair, i) => (
          <StepToolCallEntry key={pair.called.id} index={i + 1} pair={pair} workspaceId={workspaceId} />
        ))}
      </ol>
    </div>
  );
}

function StepToolCallEntry({
  index,
  pair,
  workspaceId,
}: {
  index: number;
  pair: { called: RunEventRow; result: RunEventRow | null };
  workspaceId: WorkspaceId;
}) {
  const [open, setOpen] = useState(false);
  const toolSlug = pair.called.message ?? "(unknown tool)";
  const args = (pair.called.payload as { arguments?: unknown } | undefined)?.arguments;
  const result = pair.result?.payload;
  const success =
    pair.result === null
      ? null
      : Boolean((pair.result.payload as { success?: boolean } | undefined)?.success);
  const error = (pair.result?.payload as { error?: string | null } | undefined)?.error;

  return (
    <li>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-2 rounded-sm px-2 py-1 text-left hover:bg-canvas-panel"
      >
        <div className="flex min-w-0 items-center gap-2">
          <span className="font-mono text-[10px] text-ink-mute">{index.toString().padStart(2, "0")}</span>
          <ToolCallStatusIcon state={success === null ? "pending" : success ? "ok" : "err"} />
          <span className="truncate text-xs font-medium text-ink">{toolSlug}</span>
          {pair.called.toolId && (
            <Link
              to="/workspaces/$workspaceId/tools/$toolId"
              params={{ workspaceId, toolId: pair.called.toolId as never }}
              onClick={(e) => e.stopPropagation()}
              title="Open tool"
              className="text-[10px] uppercase tracking-eyebrow text-ink-mute hover:text-sodium"
            >
              open
            </Link>
          )}
        </div>
        <span className="text-[10px] text-ink-mute">{open ? "−" : "+"}</span>
      </button>
      {open && (
        <div className="flex flex-col gap-1.5 border-t border-canvas-rule px-3 py-2">
          {error && (
            <div className="rounded-sm border border-signal-err/40 bg-signal-err/5 px-2 py-1 text-[11px] text-signal-err">
              {error}
            </div>
          )}
          <JsonBlock label="Arguments" value={args} />
          {pair.result ? (
            <JsonBlock label="Result" value={result} />
          ) : (
            <p className="text-[11px] text-ink-mute">No result recorded — the agent never received this tool's reply (likely failed before the next LLM hop).</p>
          )}
        </div>
      )}
    </li>
  );
}

function ToolCallStatusIcon({ state }: { state: "ok" | "err" | "pending" }) {
  const common = "h-3 w-3";
  if (state === "ok") return <CheckCircle2 className={cn(common, "text-signal-ok")} strokeWidth={2} />;
  if (state === "err") return <XCircle className={cn(common, "text-signal-err")} strokeWidth={2} />;
  return <Clock className={cn(common, "text-ink-mute")} strokeWidth={2} />;
}

function NodeStatusIcon({ status }: { status: RunNodeStatus }) {
  const common = "h-3.5 w-3.5";
  switch (status) {
    case "completed":
      return <CheckCircle2 className={cn(common, "text-signal-ok")} strokeWidth={2} />;
    case "running":
      return <Loader2 className={cn(common, "animate-spin text-sodium")} strokeWidth={2} />;
    case "queued":
    case "waiting":
      return <Clock className={cn(common, "text-ink-mute")} strokeWidth={2} />;
    case "failed":
      return <XCircle className={cn(common, "text-signal-err")} strokeWidth={2} />;
    case "skipped":
    case "cancelled":
      return <AlertCircle className={cn(common, "text-ink-mute")} strokeWidth={2} />;
  }
}

function RunStatusChip({ status }: { status: RunStatus }) {
  switch (status) {
    case "completed":
      return <Chip tone="ok">completed</Chip>;
    case "running":
      return <Chip tone="warn">running</Chip>;
    case "queued":
    case "waiting":
      return <Chip tone="default">{status}</Chip>;
    case "failed":
      return <Chip tone="err">failed</Chip>;
    case "cancelled":
      return <Chip tone="default">cancelled</Chip>;
  }
}

// ──────────────────────────────────────────────────────────────────────
// Tool call counts — derived from run.nodes + run.events
// ──────────────────────────────────────────────────────────────────────

type ToolCallCount = {
  nodeId: string;
  nodeLabel: string;
  toolId: string;
  callCount: number;
};

function countToolCalls(nodes: RunNode[], events: RunEventRow[]): ToolCallCount[] {
  const result: ToolCallCount[] = [];

  // 1. Explicit `tool` nodes — each one is a single call by construction.
  for (const n of nodes) {
    if (n.nodeType !== "tool" || !n.toolId) continue;
    result.push({
      nodeId: n.nodeId,
      nodeLabel: n.nodeLabel || n.nodeId,
      toolId: n.toolId,
      callCount: 1,
    });
  }

  // 2. Agent-bound tool calls — surfaced through the event stream.
  //    Group by (nodeId, toolId) so an agent that calls the same tool
  //    multiple times shows up as one row with `callCount > 1`.
  const byKey = new Map<string, ToolCallCount>();
  for (const e of events) {
    if (e.eventType !== "tool.called" || !e.toolId || !e.nodeId) continue;
    const key = `${e.nodeId}:${e.toolId}`;
    const existing = byKey.get(key);
    if (existing) {
      existing.callCount += 1;
    } else {
      const node = nodes.find((n) => n.nodeId === e.nodeId);
      byKey.set(key, {
        nodeId: e.nodeId,
        nodeLabel: node?.nodeLabel || e.nodeId,
        toolId: e.toolId,
        callCount: 1,
      });
    }
  }
  for (const entry of byKey.values()) result.push(entry);

  return result;
}

function ToolCallRow({ workspaceId, row }: { workspaceId: WorkspaceId; row: ToolCallCount }) {
  const { data: tool } = useTool(workspaceId, row.toolId as never);
  return (
    <li className="flex items-center justify-between gap-3 px-4 py-2 text-xs">
      <div className="min-w-0">
        <div className="truncate font-medium text-ink">{tool?.name ?? row.toolId.slice(0, 8)}</div>
        <div className="text-[10px] text-ink-mute">
          step <span className="font-mono">{row.nodeId}</span> ({row.nodeLabel})
        </div>
      </div>
      <Chip tone="default">×{row.callCount}</Chip>
    </li>
  );
}

function AgentRefLine({ workspaceId, agentId }: { workspaceId: WorkspaceId; agentId: string }) {
  const { data: agent } = useAgent(workspaceId, agentId as never);
  return (
    <div className="flex items-center gap-2 text-[11px] text-ink-dim">
      <span className="text-ink-mute">Agent:</span>
      <span className="font-medium text-ink">{agent?.name ?? agentId.slice(0, 8)}</span>
      {agent && (
        <span className="font-mono text-[10px] text-ink-mute">
          {agent.modelProvider} · {agent.modelName}
        </span>
      )}
      <Link
        to="/workspaces/$workspaceId/agents/$agentId"
        params={{ workspaceId, agentId: agentId as never }}
        title="Open agent details"
        className="ml-auto inline-flex items-center gap-1 text-[10px] font-medium uppercase tracking-eyebrow text-sodium hover:underline"
      >
        Open
        <ExternalLink size={10} strokeWidth={1.8} />
      </Link>
    </div>
  );
}

function ToolRefLine({ workspaceId, toolId }: { workspaceId: WorkspaceId; toolId: string }) {
  const { data: tool } = useTool(workspaceId, toolId as never);
  return (
    <div className="flex items-center gap-2 text-[11px] text-ink-dim">
      <span className="text-ink-mute">Tool:</span>
      <span className="font-medium text-ink">{tool?.name ?? toolId.slice(0, 8)}</span>
      {tool && (
        <span className="font-mono text-[10px] text-ink-mute">
          {tool.type} · v{tool.version}
        </span>
      )}
      <Link
        to="/workspaces/$workspaceId/tools/$toolId"
        params={{ workspaceId, toolId: toolId as never }}
        title="Open tool details"
        className="ml-auto inline-flex items-center gap-1 text-[10px] font-medium uppercase tracking-eyebrow text-sodium hover:underline"
      >
        Open
        <ExternalLink size={10} strokeWidth={1.8} />
      </Link>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// JSON block helpers
// ──────────────────────────────────────────────────────────────────────

function JsonBlock({ label, value }: { label: string; value: unknown }) {
  const text = safeStringify(value);
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-eyebrow text-ink-mute">{label}</span>
        <CopyJsonButton text={text} />
      </div>
      <pre className="max-h-64 overflow-auto rounded-md border border-canvas-rule bg-canvas px-2.5 py-2 font-mono text-[11px] leading-relaxed text-ink-dim">
        {text}
      </pre>
    </div>
  );
}

function CollapsibleJson({ label, value, defaultOpen }: { label: string; value: unknown; defaultOpen?: boolean }) {
  const text = safeStringify(value);
  return (
    <details className="rounded-md border border-canvas-rule bg-canvas-panel" open={defaultOpen}>
      <summary className="flex cursor-pointer items-center justify-between gap-2 px-4 py-2">
        <span className="text-[10px] font-semibold uppercase tracking-eyebrow text-ink-mute">{label}</span>
        {/* stopPropagation so clicking the copy button doesn't also toggle
            the <details>. Same trick we use on row-level action pills. */}
        <span onClick={(e) => e.stopPropagation()}>
          <CopyJsonButton text={text} />
        </span>
      </summary>
      <pre className="max-h-72 overflow-auto border-t border-canvas-rule bg-canvas px-4 py-2 font-mono text-[11px] leading-relaxed text-ink-dim">
        {text}
      </pre>
    </details>
  );
}

/**
 * "Copy entire run" — bundles the run metadata, initial input, final state,
 * every step row, and the event stream into a single pretty-JSON blob.
 * Convenient for pasting into a bug report or diffing two runs.
 */
function CopyRunButton({ run }: { run: RunDetail }) {
  const [copied, setCopied] = useState(false);
  const onCopy = async () => {
    const bundle = {
      run: {
        id: run.id,
        workspace_id: run.workspaceId,
        workflow_id: run.workflowId ?? null,
        status: run.status,
        trigger: { type: run.triggerType, source: run.triggerSource ?? null },
        error_message: run.errorMessage ?? null,
        tokens: { input: run.totalInputTokens, output: run.totalOutputTokens },
        cost_usd: run.totalCostUsd,
        timestamps: {
          created_at: run.createdAt,
          updated_at: run.updatedAt,
          started_at: run.startedAt ?? null,
          completed_at: run.completedAt ?? null,
        },
      },
      input: run.input,
      output: run.output,
      nodes: run.nodes,
      events: run.events,
    };
    try {
      await navigator.clipboard.writeText(safeStringify(bundle));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Insecure context / permission denied — fall back to no-op; the
      // per-block copy buttons still cover the user's escape hatch.
    }
  };
  return (
    <button
      type="button"
      onClick={onCopy}
      title="Copy entire run as JSON"
      aria-label="Copy entire run as JSON"
      className="inline-flex items-center gap-1 rounded-md border border-canvas-rule px-2 py-1 text-[10px] font-medium uppercase tracking-eyebrow text-ink-dim hover:border-sodium hover:text-sodium"
    >
      {copied ? <Tick size={11} strokeWidth={1.8} /> : <Copy size={11} strokeWidth={1.8} />}
      {copied ? "copied run" : "copy run"}
    </button>
  );
}

function CopyJsonButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const onCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API requires a secure context — `pre` is selectable as
      // a fallback when permission is denied. Silently absorb the error.
    }
  };
  return (
    <button
      type="button"
      onClick={onCopy}
      aria-label="Copy JSON"
      title="Copy JSON"
      className="inline-flex items-center gap-1 rounded-md border border-canvas-rule px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-eyebrow text-ink-mute hover:border-sodium hover:text-sodium"
    >
      {copied ? <Tick size={10} strokeWidth={1.8} /> : <Copy size={10} strokeWidth={1.8} />}
      {copied ? "copied" : "copy"}
    </button>
  );
}

function safeStringify(value: unknown): string {
  try {
    return JSON.stringify(deepParseJson(value), null, 2);
  } catch {
    return String(value);
  }
}

/**
 * Recursively replace any string that's actually a JSON object/array with
 * the parsed value, so nested JSON-as-string blobs (e.g. agent ``content``
 * holding ``"{\"intent\":...}"``) pretty-print as structured JSON instead
 * of one escaped one-liner. Cycle-safe via the seen set — JSON can't
 * actually loop, but `deepParseJson` is called on arbitrary input.
 */
function deepParseJson(value: unknown, seen = new WeakSet<object>()): unknown {
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (
      (trimmed.startsWith("{") && trimmed.endsWith("}")) ||
      (trimmed.startsWith("[") && trimmed.endsWith("]"))
    ) {
      try {
        const parsed: unknown = JSON.parse(trimmed);
        return deepParseJson(parsed, seen);
      } catch {
        return value;
      }
    }
    return value;
  }
  if (value === null || typeof value !== "object") return value;
  if (seen.has(value)) return value;
  seen.add(value);
  if (Array.isArray(value)) return value.map((item) => deepParseJson(item, seen));
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(value)) {
    out[k] = deepParseJson(v, seen);
  }
  return out;
}

function formatDuration(startedAt: string | undefined, completedAt: string | undefined): string {
  if (!startedAt) return "—";
  const start = new Date(startedAt).getTime();
  const end = completedAt ? new Date(completedAt).getTime() : Date.now();
  const ms = end - start;
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)} s`;
  const m = Math.floor(ms / 60_000);
  const s = Math.round((ms % 60_000) / 1000);
  return `${m}m ${s}s`;
}

function formatRelative(iso: string): string {
  const t = new Date(iso).getTime();
  const diff = Date.now() - t;
  const s = Math.round(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.round(h / 24);
  return `${d}d ago`;
}
