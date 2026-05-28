import { useMemo, useState } from "react";

import { useAuth } from "@/app/auth";
import { useWorkspaces, WorkspaceCard, type WorkspaceSummary } from "@/entities/workspace";
import { CreateWorkspaceCard, CreateWorkspaceTile } from "@/features/create-workspace";
import { Chip, SectionHeader } from "@/shared/ui";

/**
 * Landing page — grid of workspaces.
 *
 * Layout rules:
 * - First grid cell is ALWAYS the "create workspace" tile (or the inline
 *   create form when the user clicks into it).
 * - 3 columns at all sizes ≥ sm, so every card is exactly 33% wide — even
 *   when there's only the create tile.
 * - Existing workspaces are sorted newest-first by `createdAt`.
 */
export function DashboardPage() {
  const { user } = useAuth();
  const firstName = user?.name?.split(" ")[0] || user?.email?.split("@")[0] || "there";

  const workspaces = useWorkspaces();
  const [isCreating, setIsCreating] = useState(false);

  const sorted: WorkspaceSummary[] = useMemo(() => {
    const items = workspaces.data?.items ?? [];
    return [...items].sort((a, b) => (a.createdAt < b.createdAt ? 1 : a.createdAt > b.createdAt ? -1 : 0));
  }, [workspaces.data?.items]);

  return (
    <div className="mx-auto w-full max-w-[1320px] px-6 py-8">
      <SectionHeader
        eyebrow="Mission control"
        title={
          <>
            Good to see you, <span className="font-medium text-sodium">{firstName}</span>.
          </>
        }
        meta="Pick a workspace to see its workflows."
        right={workspaces.data ? <Chip tone="default">{sorted.length} workspaces</Chip> : null}
      />

      <div className="hairline-x mt-6" />

      <section className="mt-6">
        {workspaces.isError && (
          <div className="mb-4 rounded-md border border-signal-err/40 bg-signal-err/5 p-4 text-sm text-signal-err">
            {workspaces.error.message}
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {isCreating ? (
            <CreateWorkspaceCard onSuccess={() => setIsCreating(false)} onCancel={() => setIsCreating(false)} />
          ) : (
            <CreateWorkspaceTile onClick={() => setIsCreating(true)} />
          )}

          {workspaces.isPending &&
            !workspaces.data &&
            Array.from({ length: 2 }).map((_, i) => (
              <div
                key={`skeleton-${i}`}
                aria-hidden
                className="h-[156px] animate-pulse rounded-md border border-canvas-rule bg-canvas-panel/60"
              />
            ))}

          {sorted.map((ws) => (
            <WorkspaceCard key={ws.id} workspace={ws} />
          ))}
        </div>
      </section>
    </div>
  );
}
