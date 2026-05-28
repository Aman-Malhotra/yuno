import { useEffect } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowLeft, Settings } from "lucide-react";
import { ReactFlowProvider } from "reactflow";

import type { Workflow, WorkflowId } from "@/entities/workflow";
import type { WorkspaceId } from "@/entities/workspace";

import { useGraphAutosave } from "../lib/use-graph-autosave";
import { useWorkflowBuilderStore } from "../model/workflow-builder.store";
import { SaveStatusIndicator } from "./SaveStatusIndicator";
import { WorkflowCanvas } from "./WorkflowCanvas";
import { WorkflowNodePalette } from "./WorkflowNodePalette";
import { WorkflowRightPanel } from "./WorkflowRightPanel";

type Props = {
  workspaceId: WorkspaceId;
  workflowId: WorkflowId;
  workflow: Workflow;
  /** Disable autosave (e.g. during a publish flow or read-only preview). */
  readOnly?: boolean;
};

/**
 * Mount the builder against a *loaded* workflow. The parent is responsible
 * for creating the workflow first (so we always have an id to PATCH).
 *
 * Loading the graph into the store happens once per `workflowId` — when it
 * changes (navigating between workflows in the same SPA shell), we reseed.
 */
export function WorkflowBuilderPage({ workspaceId, workflowId, workflow, readOnly = false }: Props) {
  const setGraph = useWorkflowBuilderStore((s) => s.setGraph);

  useEffect(() => {
    setGraph(workflow.graph);
    // We deliberately key on `workflowId` only, not the whole workflow —
    // autosave PATCHes return the canonical detail and we don't want a
    // round-trip to reset the local canvas mid-edit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowId]);

  useGraphAutosave(workspaceId, workflowId);

  return (
    // Provider lifted above the palette so its agent tiles can drive the
    // viewport (click → centerOnNode) via `useReactFlow`.
    <ReactFlowProvider>
      <div className="flex h-[calc(100vh-3.5rem)] flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-canvas-rule bg-canvas-panel px-4 py-2">
          <div className="flex min-w-0 items-center gap-3">
            <Link
              to="/workspaces/$workspaceId/workflows"
              params={{ workspaceId }}
              aria-label="Back to workflows"
              title="Back to workflows"
              className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-canvas-rule text-ink-mute hover:border-sodium hover:text-ink"
            >
              <ArrowLeft size={14} strokeWidth={1.8} />
            </Link>
            <div className="min-w-0">
              <div className="truncate text-sm font-medium text-ink">{workflow.name}</div>
              <div className="font-mono text-[11px] text-ink-mute">{workflow.slug}</div>
            </div>
            <Link
              to="/workspaces/$workspaceId/workflows/$workflowId/settings"
              params={{ workspaceId, workflowId }}
              aria-label="Workflow settings"
              title="Workflow settings"
              className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-canvas-rule text-ink-mute hover:border-sodium hover:text-ink"
            >
              <Settings size={14} strokeWidth={1.8} />
            </Link>
          </div>
          <SaveStatusIndicator readOnly={readOnly} />
        </header>

        <div className="flex min-h-0 flex-1">
          <WorkflowNodePalette workspaceId={workspaceId} />
          <main className="flex-1">
            <WorkflowCanvas />
          </main>
          <WorkflowRightPanel workspaceId={workspaceId} workflowId={workflowId} />
        </div>
      </div>
    </ReactFlowProvider>
  );
}
