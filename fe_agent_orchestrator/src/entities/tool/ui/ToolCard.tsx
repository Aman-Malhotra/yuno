import { Link } from "@tanstack/react-router";
import { Wrench } from "lucide-react";

import type { WorkspaceId } from "@/entities/workspace";
import type { ToolSummary } from "../model/tool.types";
import { ToolStatusChip } from "./ToolStatusChip";
import { ToolTypeChip } from "./ToolTypeChip";

type Props = {
  tool: ToolSummary;
  workspaceId: WorkspaceId;
};

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return iso;
  }
}

export function ToolCard({ tool, workspaceId }: Props) {
  return (
    <Link
      to="/workspaces/$workspaceId/tools/$toolId"
      params={{ workspaceId, toolId: tool.id }}
      className="group flex flex-col gap-3 rounded-md border border-canvas-rule bg-canvas-panel p-4 transition-colors hover:border-sodium"
    >
      <header className="flex items-start justify-between gap-3">
        <span
          aria-hidden
          className="flex h-9 w-9 items-center justify-center rounded-md border border-canvas-ruleStrong bg-canvas-inset text-ink-mute group-hover:text-sodium"
        >
          <Wrench size={16} strokeWidth={1.6} />
        </span>
        <div className="flex items-center gap-1.5">
          <ToolTypeChip type={tool.type} />
          <ToolStatusChip status={tool.status} />
        </div>
      </header>

      <div className="min-w-0">
        <h3 className="truncate text-sm font-medium text-ink">{tool.name}</h3>
        <p className="mt-0.5 truncate font-mono text-[11px] text-ink-mute">{tool.slug}</p>
        <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-ink-dim">{tool.description}</p>
      </div>

      <footer className="flex items-center justify-between border-t border-canvas-rule pt-3 text-[10px] uppercase tracking-eyebrow text-ink-faint">
        <span>
          v{tool.version} · {tool.category}
        </span>
        <span className="font-mono">updated {formatDate(tool.updatedAt)}</span>
      </footer>
    </Link>
  );
}
