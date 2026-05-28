import { useMemo, useState } from "react";
import { useParams } from "@tanstack/react-router";
import { ArrowDownToLine, ArrowUpFromLine, Coins } from "lucide-react";

import { type AgentCostRow, useAgentCosts } from "@/entities/cost";
import type { WorkspaceId } from "@/entities/workspace";
import { Chip, SectionHeader } from "@/shared/ui";
import { cn } from "@/shared/lib/cn";

type Range = "all" | "24h" | "7d";

const RANGE_OPTIONS: { value: Range; label: string }[] = [
  { value: "all", label: "All time" },
  { value: "24h", label: "Last 24h" },
  { value: "7d", label: "Last 7d" },
];

// Pin `since` to the start of the current hour so the value is stable
// across re-renders. Without this, every render produces a fresh ISO →
// react-query treats it as a new queryKey → refetches → re-renders →
// new ISO. We saw this cause hundreds of requests on the Costs tab.
function rangeToSinceIso(range: Range): string | undefined {
  if (range === "all") return undefined;
  const windowMs = range === "24h" ? 24 * 3600_000 : 7 * 24 * 3600_000;
  const now = Date.now();
  // Snap "now" down to the current hour boundary. The window slides by
  // an hour at most, which is plenty fresh for a cost dashboard.
  const snappedNow = Math.floor(now / 3600_000) * 3600_000;
  return new Date(snappedNow - windowMs).toISOString();
}

export function WorkspaceCostsPage() {
  const { workspaceId } = useParams({ from: "/protected/workspaces/$workspaceId" });
  const wsId = workspaceId as WorkspaceId;
  const [range, setRange] = useState<Range>("all");

  // Recompute the ISO only when the selected range changes — NOT on every
  // render. The memo guards react-query's queryKey from churning, which
  // was causing the Costs tab to fire hundreds of fetches per session.
  const since = useMemo(() => rangeToSinceIso(range), [range]);

  const costs = useAgentCosts(wsId, since);

  const summary = costs.data;
  const maxTotal = useMemo(
    () => (summary?.items[0]?.totalTokens ?? 0) || 1,
    [summary?.items],
  );

  return (
    <div className="mx-auto w-full max-w-[1180px] px-6 py-8">
      <SectionHeader
        title="Costs"
        meta="Token usage per agent. Aggregated from completed agent turns."
        right={
          summary ? (
            <Chip tone="default">{summary.totalTokens.toLocaleString()} tokens total</Chip>
          ) : null
        }
      />

      <div className="hairline-x mt-6" />

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-faint">
          Window
        </span>
        <div className="flex gap-1 rounded-sm border border-canvas-rule bg-canvas-panel p-0.5">
          {RANGE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setRange(opt.value)}
              className={cn(
                "rounded-sm px-3 py-1 text-[12px] transition-colors",
                range === opt.value
                  ? "bg-sodium-tint text-sodium"
                  : "text-ink-mute hover:bg-canvas-inset hover:text-ink",
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {summary && (
        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <SummaryTile
            icon={<ArrowDownToLine size={14} strokeWidth={1.6} />}
            label="Input tokens"
            value={summary.totalInputTokens}
          />
          <SummaryTile
            icon={<ArrowUpFromLine size={14} strokeWidth={1.6} />}
            label="Output tokens"
            value={summary.totalOutputTokens}
          />
          <SummaryTile
            icon={<Coins size={14} strokeWidth={1.6} />}
            label="Total tokens"
            value={summary.totalTokens}
            emphasised
          />
        </div>
      )}

      <section className="mt-6">
        {costs.isError && (
          <div className="rounded-md border border-signal-err/40 bg-signal-err/5 p-4 text-sm text-signal-err">
            {costs.error?.message ?? "Couldn't load costs."}
          </div>
        )}

        {costs.isPending && !summary && (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                aria-hidden
                className="h-[64px] animate-pulse rounded-md border border-canvas-rule bg-canvas-panel/60"
              />
            ))}
          </div>
        )}

        {summary && summary.items.length === 0 && (
          <div className="rounded-md border border-canvas-rule bg-canvas-panel/40 p-6 text-center text-sm text-ink-mute">
            No agent runs yet. Trigger a workflow to populate the cost board.
          </div>
        )}

        {summary && summary.items.length > 0 && (
          <ul className="space-y-2">
            {summary.items.map((row) => (
              <AgentRow key={row.agentId} row={row} maxTotal={maxTotal} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────── */

function SummaryTile({
  icon,
  label,
  value,
  emphasised,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  emphasised?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-md border bg-canvas-panel px-4 py-3",
        emphasised ? "border-sodium/40" : "border-canvas-rule",
      )}
    >
      <div className="flex items-center gap-1.5 text-ink-mute">
        {icon}
        <span className="font-mono text-[10px] uppercase tracking-eyebrow">{label}</span>
      </div>
      <div
        className={cn(
          "mt-1 font-mono text-[20px]",
          emphasised ? "text-sodium" : "text-ink",
        )}
      >
        {value.toLocaleString()}
      </div>
    </div>
  );
}

function AgentRow({ row, maxTotal }: { row: AgentCostRow; maxTotal: number }) {
  const pct = Math.max(2, Math.round((row.totalTokens / maxTotal) * 100));
  return (
    <li className="rounded-md border border-canvas-rule bg-canvas-panel px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-[13px] font-medium text-ink">{row.name}</span>
            <code className="truncate font-mono text-[10px] text-ink-mute">{row.slug}</code>
          </div>
          <div className="mt-0.5 flex flex-wrap items-center gap-3 text-[10px] text-ink-mute">
            <span>
              <span className="text-ink-faint">model:</span>{" "}
              <span className="font-mono">{row.modelProvider}/{row.modelName}</span>
            </span>
            <span>
              <span className="text-ink-faint">runs:</span> {row.runCount}
            </span>
            {row.lastSeenAt && (
              <span className="font-mono">last {row.lastSeenAt}</span>
            )}
          </div>
        </div>
        <div className="shrink-0 text-right">
          <div className="font-mono text-[13px] text-ink">
            {row.totalTokens.toLocaleString()}
          </div>
          <div className="font-mono text-[10px] text-ink-mute">
            in {row.inputTokens.toLocaleString()} · out {row.outputTokens.toLocaleString()}
          </div>
        </div>
      </div>
      <div
        aria-hidden
        className="mt-2 h-1.5 overflow-hidden rounded-full bg-canvas-inset"
      >
        <div
          className="h-full rounded-full bg-sodium"
          style={{ width: `${pct}%` }}
        />
      </div>
    </li>
  );
}
