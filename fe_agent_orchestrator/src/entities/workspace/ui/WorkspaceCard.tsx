import { Link } from "@tanstack/react-router";
import { Folder } from "lucide-react";

import type { WorkspaceSummary } from "../model/workspace.types";
import { WorkspaceRoleChip } from "./WorkspaceRoleChip";

function formatJoined(iso: string): string {
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

export function WorkspaceCard({ workspace }: { workspace: WorkspaceSummary }) {
  return (
    <Link
      to="/workspaces/$workspaceId/workflows"
      params={{ workspaceId: workspace.id }}
      className="group relative flex flex-col gap-3 rounded-md border border-canvas-rule bg-canvas-panel p-4 transition-colors hover:border-sodium"
    >
      <div className="flex items-start justify-between gap-3">
        <span
          aria-hidden
          className="flex h-9 w-9 items-center justify-center rounded-md border border-canvas-ruleStrong bg-canvas-inset text-ink-mute group-hover:text-sodium"
        >
          <Folder size={16} strokeWidth={1.6} />
        </span>
        <WorkspaceRoleChip role={workspace.role} />
      </div>

      <div className="min-w-0">
        <h3 className="truncate text-sm font-medium text-ink">{workspace.name}</h3>
        <p className="mt-0.5 truncate font-mono text-[11px] text-ink-mute">{workspace.slug}</p>
      </div>

      <footer className="flex items-center justify-between border-t border-canvas-rule pt-3 text-[10px] uppercase tracking-eyebrow text-ink-faint">
        <span>since {formatJoined(workspace.createdAt)}</span>
        <span className="font-mono">open →</span>
      </footer>
    </Link>
  );
}
