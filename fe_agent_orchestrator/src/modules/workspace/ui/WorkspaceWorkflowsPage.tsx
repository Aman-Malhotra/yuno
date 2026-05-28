import { useMemo } from "react";
import { useParams } from "@tanstack/react-router";

import { useWorkflowsInWorkspace, WorkflowCard, type WorkflowSummary } from "@/entities/workflow";
import { type WorkspaceId } from "@/entities/workspace";
import { CreateWorkflowTile } from "@/features/create-workflow";
import { Chip, SectionHeader } from "@/shared/ui";

export function WorkspaceWorkflowsPage() {
  const { workspaceId } = useParams({ from: "/protected/workspaces/$workspaceId" });
  const wsId = workspaceId as WorkspaceId;

  const workflows = useWorkflowsInWorkspace(wsId);

  const sorted: WorkflowSummary[] = useMemo(() => {
    const items = workflows.data?.items ?? [];
    return [...items].sort((a, b) => (a.createdAt < b.createdAt ? 1 : a.createdAt > b.createdAt ? -1 : 0));
  }, [workflows.data?.items]);

  return (
    <div className="mx-auto w-full max-w-[1180px] px-6 py-8">
      <SectionHeader
        title="Workflows"
        meta="Pick one to open its builder canvas."
        right={workflows.data ? <Chip tone="default">{workflows.data.total} total</Chip> : null}
      />

      <div className="hairline-x mt-6" />

      <section className="mt-6">
        {workflows.isError && (
          <div className="mb-4 rounded-md border border-signal-err/40 bg-signal-err/5 p-4 text-sm text-signal-err">
            {workflows.error.message}
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <CreateWorkflowTile workspaceId={wsId} />

          {workflows.isPending &&
            !workflows.data &&
            Array.from({ length: 2 }).map((_, i) => (
              <div
                key={`skel-${i}`}
                aria-hidden
                className="h-[156px] animate-pulse rounded-md border border-canvas-rule bg-canvas-panel/60"
              />
            ))}

          {sorted.map((wf) => (
            <WorkflowCard key={wf.id} workflow={wf} />
          ))}
        </div>
      </section>
    </div>
  );
}
