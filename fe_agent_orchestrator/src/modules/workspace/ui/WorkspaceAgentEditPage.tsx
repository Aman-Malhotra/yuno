import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";

import { useAgent, type AgentId } from "@/entities/agent";
import type { WorkspaceId } from "@/entities/workspace";
import { CreateAgentForm } from "@/features/create-agent";
import { SectionHeader } from "@/shared/ui";

export function WorkspaceAgentEditPage() {
  const { workspaceId, agentId } = useParams({
    from: "/protected/workspaces/$workspaceId/agents/$agentId/edit",
  });
  const wsId = workspaceId as WorkspaceId;
  const aId = agentId as AgentId;

  const navigate = useNavigate();
  const agent = useAgent(wsId, aId);

  return (
    <div className="mx-auto w-full max-w-[860px] px-6 py-8">
      <Link
        to="/workspaces/$workspaceId/agents/$agentId"
        params={{ workspaceId: wsId, agentId: aId }}
        className="mb-4 inline-flex items-center gap-1.5 text-[11px] uppercase tracking-eyebrow text-ink-mute hover:text-ink"
      >
        <ArrowLeft size={12} strokeWidth={1.8} />
        back to agent
      </Link>

      <SectionHeader
        title={agent.data ? `Edit · ${agent.data.name}` : "Edit agent"}
        meta="Tweak any field — including attached tools — then save."
      />

      <div className="hairline-x mt-6" />

      <section className="mt-6 rounded-md border border-canvas-rule bg-canvas-panel p-6">
        {agent.isPending && <p className="text-sm text-ink-mute">Loading agent…</p>}
        {agent.isError && (
          <p className="rounded-sm border border-signal-err/40 bg-signal-err/5 px-3 py-2 text-xs text-signal-err">
            {agent.error.message}
          </p>
        )}
        {agent.data && (
          <CreateAgentForm
            workspaceId={wsId}
            agent={agent.data}
            onSuccess={() =>
              navigate({
                to: "/workspaces/$workspaceId/agents/$agentId",
                params: { workspaceId: wsId, agentId: aId },
              })
            }
            onCancel={() =>
              navigate({
                to: "/workspaces/$workspaceId/agents/$agentId",
                params: { workspaceId: wsId, agentId: aId },
              })
            }
          />
        )}
      </section>
    </div>
  );
}
