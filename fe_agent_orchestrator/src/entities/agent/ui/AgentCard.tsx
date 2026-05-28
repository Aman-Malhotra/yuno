import { Link } from "@tanstack/react-router";
import { Bot } from "lucide-react";

import type { WorkspaceId } from "@/entities/workspace";
import type { AgentSummary } from "../model/agent.types";

function formatCreated(iso: string): string {
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

type Props = {
  agent: AgentSummary;
  workspaceId: WorkspaceId;
};

export function AgentCard({ agent, workspaceId }: Props) {
  return (
    <Link
      to="/workspaces/$workspaceId/agents/$agentId"
      params={{ workspaceId, agentId: agent.id }}
      className="group flex flex-col gap-3 rounded-md border border-canvas-rule bg-canvas-panel p-4 transition-colors hover:border-sodium"
    >
      <header className="flex items-start justify-between gap-3">
        <span
          aria-hidden
          className="flex h-9 w-9 items-center justify-center rounded-md border border-canvas-ruleStrong bg-canvas-inset text-ink-mute group-hover:text-sodium"
        >
          <Bot size={16} strokeWidth={1.6} />
        </span>
      </header>

      <div className="min-w-0">
        <h3 className="truncate text-sm font-medium text-ink">{agent.name}</h3>
        {agent.description && (
          <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-ink-dim">{agent.description}</p>
        )}
      </div>

      <footer className="flex items-center justify-between border-t border-canvas-rule pt-3 text-[10px] uppercase tracking-eyebrow text-ink-faint">
        <span>created {formatCreated(agent.createdAt)}</span>
        <span className="font-mono">open →</span>
      </footer>
    </Link>
  );
}
