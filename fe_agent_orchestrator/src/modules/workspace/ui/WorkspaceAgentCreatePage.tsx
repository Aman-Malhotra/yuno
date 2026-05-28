import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";

import type { WorkspaceId } from "@/entities/workspace";
import { CreateAgentForm } from "@/features/create-agent";
import { SectionHeader } from "@/shared/ui";

export function WorkspaceAgentCreatePage() {
  const { workspaceId } = useParams({ from: "/protected/workspaces/$workspaceId" });
  const wsId = workspaceId as WorkspaceId;
  const navigate = useNavigate();

  return (
    <div className="mx-auto w-full max-w-[860px] px-6 py-8">
      <Link
        to="/workspaces/$workspaceId/agents"
        params={{ workspaceId: wsId }}
        className="mb-4 inline-flex items-center gap-1.5 text-[11px] uppercase tracking-eyebrow text-ink-mute hover:text-ink"
      >
        <ArrowLeft size={12} strokeWidth={1.8} />
        all agents
      </Link>

      <SectionHeader
        title="New agent"
        meta="Configure identity, model, key and tools. Defaults can be edited later from the agent detail page."
      />

      <div className="hairline-x mt-6" />

      <section className="mt-6 rounded-md border border-canvas-rule bg-canvas-panel p-6">
        <CreateAgentForm
          workspaceId={wsId}
          onSuccess={(agent) =>
            navigate({
              to: "/workspaces/$workspaceId/agents/$agentId",
              params: { workspaceId: wsId, agentId: agent.id },
            })
          }
          onCancel={() => navigate({ to: "/workspaces/$workspaceId/agents", params: { workspaceId: wsId } })}
        />
      </section>
    </div>
  );
}
