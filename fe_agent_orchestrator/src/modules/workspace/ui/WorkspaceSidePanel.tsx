import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Activity, Bot, Brain, ChevronsLeft, ChevronsRight, Coins, KeyRound, Settings as SettingsIcon, Wrench, Workflow } from "lucide-react";

import { type WorkspaceId, type WorkspaceSummary, WorkspaceRoleChip } from "@/entities/workspace";
import type { IconComponent } from "@/shared/ui";
import { cn } from "@/shared/lib/cn";

type SidePanelItem = {
  to: string;
  label: string;
  icon: IconComponent;
};

const COLLAPSED_STORAGE_KEY = "yuno.workspaceSidePanel.collapsed";

function readCollapsed(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(COLLAPSED_STORAGE_KEY) === "1";
}

function buildItems(workspaceId: WorkspaceId): SidePanelItem[] {
  return [
    { to: `/workspaces/${workspaceId}/workflows`, label: "Workflows", icon: Workflow },
    { to: `/workspaces/${workspaceId}/agents`, label: "Agents", icon: Bot },
    { to: `/workspaces/${workspaceId}/tools`, label: "Tools", icon: Wrench },
    { to: `/workspaces/${workspaceId}/llm-providers`, label: "LLM Providers", icon: KeyRound },
    { to: `/workspaces/${workspaceId}/memories`, label: "Memories", icon: Brain },
    { to: `/workspaces/${workspaceId}/costs`, label: "Costs", icon: Coins },
    { to: `/workspaces/${workspaceId}/logs`, label: "Logs", icon: Activity },
    { to: `/workspaces/${workspaceId}/settings`, label: "Settings", icon: SettingsIcon },
  ];
}

type Props = {
  workspaceId: WorkspaceId;
  workspace?: WorkspaceSummary;
};

export function WorkspaceSidePanel({ workspaceId, workspace }: Props) {
  const items = buildItems(workspaceId);
  const [collapsed, setCollapsed] = useState<boolean>(readCollapsed);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(COLLAPSED_STORAGE_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  return (
    <aside
      className={cn(
        "sticky top-14 flex h-[calc(100vh-3.5rem)] shrink-0 flex-col border-r border-canvas-rule bg-canvas-panel transition-[width] duration-150",
        collapsed ? "w-[56px]" : "w-[220px]",
      )}
    >
      <header
        className={cn(
          "flex border-b border-canvas-rule",
          collapsed ? "items-center justify-center px-2 py-3" : "items-start justify-between gap-2 px-4 pb-4 pt-5",
        )}
      >
        {!collapsed && (
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span aria-hidden className="h-px w-6 bg-sodium" />
              <span className="eyebrow">Workspace</span>
            </div>
            <h2 className="mt-2 truncate text-sm font-medium text-ink" title={workspace?.name}>
              {workspace?.name ?? "Loading…"}
            </h2>
            {workspace && <p className="mt-0.5 truncate font-mono text-[10px] text-ink-mute">{workspace.slug}</p>}
          </div>
        )}
        <button
          type="button"
          onClick={() => setCollapsed((c) => !c)}
          aria-label={collapsed ? "Expand workspace panel" : "Collapse workspace panel"}
          title={collapsed ? "Expand" : "Collapse"}
          className={cn(
            "inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-sm text-ink-mute transition-colors hover:bg-canvas-inset hover:text-ink",
            collapsed ? "" : "mt-0.5",
          )}
        >
          {collapsed ? <ChevronsRight size={14} strokeWidth={1.8} /> : <ChevronsLeft size={14} strokeWidth={1.8} />}
        </button>
      </header>

      <nav
        className={cn("flex flex-1 flex-col gap-0.5 py-3", collapsed ? "px-2" : "px-2")}
        aria-label="Workspace sections"
      >
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              title={collapsed ? item.label : undefined}
              className={cn(
                "group relative flex items-center rounded-sm text-[12px] text-ink-dim transition-colors hover:bg-canvas-inset hover:text-ink",
                collapsed ? "h-9 justify-center px-0" : "gap-2.5 px-3 py-2",
              )}
              activeProps={{ className: "bg-canvas-inset text-ink" }}
            >
              {({ isActive }) => (
                <>
                  <span
                    aria-hidden
                    className={cn(
                      "absolute bottom-1 left-0 top-1 w-0.5 rounded-r",
                      isActive ? "bg-sodium shadow-[0_0_6px_rgba(198,137,34,0.55)]" : "bg-transparent",
                    )}
                  />
                  <Icon
                    size={14}
                    strokeWidth={1.6}
                    className={cn(
                      "transition-colors",
                      isActive ? "text-sodium" : "text-ink-mute group-hover:text-ink-dim",
                    )}
                  />
                  {!collapsed && <span>{item.label}</span>}
                  {collapsed && <span className="sr-only">{item.label}</span>}
                </>
              )}
            </Link>
          );
        })}
      </nav>

      {workspace && !collapsed && (
        <footer className="border-t border-canvas-rule px-4 py-3">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[9px] uppercase tracking-eyebrow text-ink-faint">your role</span>
            <WorkspaceRoleChip role={workspace.role} />
          </div>
        </footer>
      )}
    </aside>
  );
}
