import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";

import { useTool, type ToolId } from "@/entities/tool";
import type { WorkspaceId } from "@/entities/workspace";
import { CreateToolForm } from "@/features/create-tool";
import { SectionHeader } from "@/shared/ui";

export function WorkspaceToolEditPage() {
  const { workspaceId, toolId } = useParams({
    from: "/protected/workspaces/$workspaceId/tools/$toolId/edit",
  });
  const wsId = workspaceId as WorkspaceId;
  const tId = toolId as ToolId;

  const navigate = useNavigate();
  const tool = useTool(wsId, tId);

  const backToDetail = () =>
    navigate({
      to: "/workspaces/$workspaceId/tools/$toolId",
      params: { workspaceId: wsId, toolId: tId },
    });

  return (
    <div className="mx-auto w-full max-w-[860px] px-6 py-8">
      <Link
        to="/workspaces/$workspaceId/tools/$toolId"
        params={{ workspaceId: wsId, toolId: tId }}
        className="mb-4 inline-flex items-center gap-1.5 text-[11px] uppercase tracking-eyebrow text-ink-mute hover:text-ink"
      >
        <ArrowLeft size={12} strokeWidth={1.8} />
        back to tool
      </Link>

      <SectionHeader
        title={tool.data ? `Edit · ${tool.data.name}` : "Edit tool"}
        meta="Update identity, schemas, or per-type config. Optionally snapshot a new version on save."
      />

      <div className="hairline-x mt-6" />

      <section className="mt-6 rounded-md border border-canvas-rule bg-canvas-panel p-6">
        {tool.isPending && <p className="text-sm text-ink-mute">Loading tool…</p>}
        {tool.isError && (
          <p className="rounded-sm border border-signal-err/40 bg-signal-err/5 px-3 py-2 text-xs text-signal-err">
            {tool.error.message}
          </p>
        )}
        {tool.data && !tool.data.workspaceId && (
          <p className="rounded-sm border border-signal-warn/40 bg-signal-warn/5 px-3 py-2 text-xs text-ink-dim">
            This is a global built-in tool — it isn't editable from the workspace.
          </p>
        )}
        {tool.data && tool.data.workspaceId && (
          <CreateToolForm workspaceId={wsId} tool={tool.data} onSuccess={backToDetail} onCancel={backToDetail} />
        )}
      </section>
    </div>
  );
}
