import { Link, useParams } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";

import { useWorkflow, type WorkflowId } from "@/entities/workflow";
import type { WorkspaceId } from "@/entities/workspace";
import { WorkflowBuilderPage } from "@/modules/workflow-builder";

/**
 * Open-workflow canvas. Fetches the full graph (GET /workflows/{id}) and
 * mounts the connected builder — autosave PATCHes `/graph` on every
 * debounced change.
 */
export function WorkspaceWorkflowDetailPage() {
  const { workspaceId, workflowId } = useParams({
    from: "/protected/workspaces/$workspaceId/workflows/$workflowId",
  });
  const wsId = workspaceId as WorkspaceId;
  const wfId = workflowId as WorkflowId;

  const { data: workflow, isPending, error } = useWorkflow(wsId, wfId);

  if (error) {
    return (
      <div className="mx-auto w-full max-w-[1400px] px-6 py-8">
        <Link
          to="/workspaces/$workspaceId/workflows"
          params={{ workspaceId: wsId }}
          className="mb-4 inline-flex items-center gap-1.5 text-[11px] uppercase tracking-eyebrow text-ink-mute hover:text-ink"
        >
          <ArrowLeft size={12} strokeWidth={1.8} />
          all workflows
        </Link>
        <div className="rounded-md border border-signal-err/40 bg-signal-err/5 p-4 text-sm text-signal-err">
          {error.message}
        </div>
      </div>
    );
  }

  if (isPending || !workflow) {
    return (
      <div className="mx-auto w-full max-w-[1400px] px-6 py-8">
        <div className="h-[480px] animate-pulse rounded-md border border-canvas-rule bg-canvas-panel/60" />
      </div>
    );
  }

  return <WorkflowBuilderPage workspaceId={wsId} workflowId={wfId} workflow={workflow} />;
}
