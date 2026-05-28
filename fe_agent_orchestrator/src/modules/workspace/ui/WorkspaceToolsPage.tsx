import { useMemo } from "react";
import { useParams } from "@tanstack/react-router";

import { useToolsInWorkspace, ToolCard, type ToolSummary } from "@/entities/tool";
import type { WorkspaceId } from "@/entities/workspace";
import { CreateToolTile } from "@/features/create-tool";
import { Chip, SectionHeader } from "@/shared/ui";

export function WorkspaceToolsPage() {
  const { workspaceId } = useParams({ from: "/protected/workspaces/$workspaceId" });
  const wsId = workspaceId as WorkspaceId;

  const tools = useToolsInWorkspace(wsId);

  const sorted: ToolSummary[] = useMemo(() => {
    const items = tools.data?.items ?? [];
    return [...items].sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : a.updatedAt > b.updatedAt ? -1 : 0));
  }, [tools.data?.items]);

  return (
    <div className="mx-auto w-full max-w-[1180px] px-6 py-8">
      <SectionHeader
        title="Tools"
        meta="Workspace-scoped tools plus global built-ins."
        right={tools.data ? <Chip tone="default">{tools.data.total} total</Chip> : null}
      />

      <div className="hairline-x mt-6" />

      <section className="mt-6">
        {tools.isError && (
          <div className="mb-4 rounded-md border border-signal-err/40 bg-signal-err/5 p-4 text-sm text-signal-err">
            {tools.error?.message ?? "Couldn't load tools."}
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <CreateToolTile workspaceId={wsId} />

          {tools.isPending &&
            !tools.data &&
            Array.from({ length: 2 }).map((_, i) => (
              <div
                key={`skel-${i}`}
                aria-hidden
                className="h-[156px] animate-pulse rounded-md border border-canvas-rule bg-canvas-panel/60"
              />
            ))}

          {sorted.map((tool) => (
            <ToolCard key={tool.id} tool={tool} workspaceId={wsId} />
          ))}
        </div>
      </section>
    </div>
  );
}
