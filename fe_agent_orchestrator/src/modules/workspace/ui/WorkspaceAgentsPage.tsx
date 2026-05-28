import { useMemo } from "react";
import { useParams } from "@tanstack/react-router";

import { useAgentsInWorkspace, AgentCard, type AgentSummary } from "@/entities/agent";
import type { WorkspaceId } from "@/entities/workspace";
import { CreateAgentTile } from "@/features/create-agent";
import { Chip, SectionHeader } from "@/shared/ui";

export function WorkspaceAgentsPage() {
  const { workspaceId } = useParams({ from: "/protected/workspaces/$workspaceId" });
  const wsId = workspaceId as WorkspaceId;

  const agents = useAgentsInWorkspace(wsId);

  const sorted: AgentSummary[] = useMemo(() => {
    const items = agents.data?.items ?? [];
    return [...items].sort((a, b) => (a.createdAt < b.createdAt ? 1 : a.createdAt > b.createdAt ? -1 : 0));
  }, [agents.data?.items]);

  return (
    <div className="mx-auto w-full max-w-[1180px] px-6 py-8">
      <SectionHeader
        title="Agents"
        meta="Create reusable agent configurations for this workspace."
        right={agents.data ? <Chip tone="default">{agents.data.total} total</Chip> : null}
      />

      <div className="hairline-x mt-6" />

      <section className="mt-6">
        {agents.isError && (
          <div className="mb-4 rounded-md border border-signal-err/40 bg-signal-err/5 p-4 text-sm text-signal-err">
            {agents.error.message}
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <CreateAgentTile workspaceId={wsId} />

          {agents.isPending &&
            !agents.data &&
            Array.from({ length: 2 }).map((_, i) => (
              <div
                key={`skel-${i}`}
                aria-hidden
                className="h-[156px] animate-pulse rounded-md border border-canvas-rule bg-canvas-panel/60"
              />
            ))}

          {sorted.map((agent) => (
            <AgentCard key={agent.id} agent={agent} workspaceId={wsId} />
          ))}
        </div>
      </section>
    </div>
  );
}
