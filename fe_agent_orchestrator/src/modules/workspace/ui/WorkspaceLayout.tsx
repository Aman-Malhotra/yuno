import { Outlet, useParams } from "@tanstack/react-router";

import { useWorkspaces, type WorkspaceId } from "@/entities/workspace";

import { WorkspaceSidePanel } from "./WorkspaceSidePanel";

/**
 * Wraps every page under /workspaces/$workspaceId/*. Renders the left side
 * panel (workflows/agents/logs/settings) and the page outlet on the right.
 */
export function WorkspaceLayout() {
  const { workspaceId } = useParams({ from: "/protected/workspaces/$workspaceId" });
  const wsId = workspaceId as WorkspaceId;

  // Reuse the landing-page workspaces query — it's already cached, so this
  // costs nothing once the user has visited /.
  const workspaces = useWorkspaces();
  const workspace = workspaces.data?.items.find((w) => w.id === wsId);

  return (
    <div className="flex">
      <WorkspaceSidePanel workspaceId={wsId} workspace={workspace} />
      <main className="min-w-0 flex-1">
        <Outlet />
      </main>
    </div>
  );
}
