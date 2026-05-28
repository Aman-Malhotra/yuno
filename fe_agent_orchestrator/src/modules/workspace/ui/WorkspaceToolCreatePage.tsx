import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";

import type { WorkspaceId } from "@/entities/workspace";
import { CreateToolForm } from "@/features/create-tool";
import { SectionHeader } from "@/shared/ui";

export function WorkspaceToolCreatePage() {
  const { workspaceId } = useParams({ from: "/protected/workspaces/$workspaceId" });
  const wsId = workspaceId as WorkspaceId;
  const navigate = useNavigate();

  return (
    <div className="mx-auto w-full max-w-[860px] px-6 py-8">
      <Link
        to="/workspaces/$workspaceId/tools"
        params={{ workspaceId: wsId }}
        className="mb-4 inline-flex items-center gap-1.5 text-[11px] uppercase tracking-eyebrow text-ink-mute hover:text-ink"
      >
        <ArrowLeft size={12} strokeWidth={1.8} />
        all tools
      </Link>

      <SectionHeader
        title="New tool"
        meta="Register a workspace tool. Auth, guardrails and execution-policy are editable from the detail page."
      />

      <div className="hairline-x mt-6" />

      <section className="mt-6 rounded-md border border-canvas-rule bg-canvas-panel p-6">
        <CreateToolForm
          workspaceId={wsId}
          onSuccess={(tool) =>
            navigate({
              to: "/workspaces/$workspaceId/tools/$toolId",
              params: { workspaceId: wsId, toolId: tool.id },
            })
          }
          onCancel={() => navigate({ to: "/workspaces/$workspaceId/tools", params: { workspaceId: wsId } })}
        />
      </section>
    </div>
  );
}
