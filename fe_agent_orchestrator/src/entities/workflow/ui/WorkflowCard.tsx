import { Link } from "@tanstack/react-router";
import { GitBranch } from "lucide-react";

import type { WorkflowSummary } from "../model/workflow.types";
import { WorkflowStatusChip } from "./WorkflowStatusChip";

function formatUpdated(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

export function WorkflowCard({ workflow }: { workflow: WorkflowSummary }) {
  return (
    <Link
      to="/workspaces/$workspaceId/workflows/$workflowId"
      params={{ workspaceId: workflow.workspaceId, workflowId: workflow.id }}
      className="group flex flex-col gap-3 rounded-md border border-canvas-rule bg-canvas-panel p-4 transition-colors hover:border-sodium"
    >
      <header className="flex items-start justify-between gap-3">
        <span
          aria-hidden
          className="flex h-9 w-9 items-center justify-center rounded-md border border-canvas-ruleStrong bg-canvas-inset text-ink-mute group-hover:text-sodium"
        >
          <GitBranch size={16} strokeWidth={1.6} />
        </span>
        <WorkflowStatusChip status={workflow.status} />
      </header>

      <div className="min-w-0">
        <h3 className="truncate text-sm font-medium text-ink">{workflow.name}</h3>
        <p className="mt-0.5 truncate font-mono text-[11px] text-ink-mute">{workflow.slug}</p>
        {workflow.description && (
          <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-ink-dim">{workflow.description}</p>
        )}
      </div>

      <footer className="flex items-center justify-between border-t border-canvas-rule pt-3 text-[10px] uppercase tracking-eyebrow text-ink-faint">
        <span>updated {formatUpdated(workflow.updatedAt)}</span>
        <span className="font-mono">open →</span>
      </footer>
    </Link>
  );
}
