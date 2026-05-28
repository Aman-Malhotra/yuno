import { useState } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import { AlertTriangle, Trash2 } from "lucide-react";

import { useDeleteWorkspace, useWorkspaces, type WorkspaceId, WorkspaceRoleChip } from "@/entities/workspace";
import { Button, Chip, Field, Input, SectionHeader } from "@/shared/ui";
import { cn } from "@/shared/lib/cn";

export function WorkspaceSettingsPage() {
  const { workspaceId } = useParams({ from: "/protected/workspaces/$workspaceId" });
  const wsId = workspaceId as WorkspaceId;

  const navigate = useNavigate();
  const workspaces = useWorkspaces();
  const workspace = workspaces.data?.items.find((w) => w.id === wsId);
  const isOwner = workspace?.role === "owner";

  const deleteWorkspace = useDeleteWorkspace();
  const [confirmText, setConfirmText] = useState("");
  const canDelete = isOwner && workspace?.name && confirmText.trim() === workspace.name;

  const onDelete = async () => {
    if (!canDelete) return;
    await deleteWorkspace.mutateAsync(wsId);
    void navigate({ to: "/", replace: true });
  };

  return (
    <div className="mx-auto w-full max-w-[840px] px-6 py-8">
      <SectionHeader title="Settings" meta="Workspace-scoped settings." />
      <div className="hairline-x mt-6" />

      {/* Info card */}
      <section className="mt-6 rounded-md border border-canvas-rule bg-canvas-panel p-6">
        <header className="flex items-baseline justify-between">
          <div>
            <h3 className="text-sm font-medium text-ink">Workspace</h3>
            <p className="mt-1 text-xs text-ink-dim">Read-only for now. Renaming + member management land later.</p>
          </div>
          {workspace && <WorkspaceRoleChip role={workspace.role} />}
        </header>

        <dl className="mt-5 divide-y divide-canvas-rule text-sm">
          <div className="grid grid-cols-[120px_1fr] items-center gap-4 py-3">
            <dt className="eyebrow">Name</dt>
            <dd className="text-ink">{workspace?.name ?? "—"}</dd>
          </div>
          <div className="grid grid-cols-[120px_1fr] items-center gap-4 py-3">
            <dt className="eyebrow">Slug</dt>
            <dd>
              <code className="font-mono text-xs text-ink-dim">{workspace?.slug ?? "—"}</code>
            </dd>
          </div>
          <div className="grid grid-cols-[120px_1fr] items-center gap-4 py-3">
            <dt className="eyebrow">ID</dt>
            <dd>
              <code className="font-mono text-xs text-ink-dim">{wsId}</code>
            </dd>
          </div>
        </dl>
      </section>

      {/* Danger zone */}
      <section
        className={cn(
          "mt-6 rounded-md border p-6",
          isOwner ? "border-signal-err/40 bg-signal-err/[0.03]" : "border-canvas-rule bg-canvas-panel",
        )}
      >
        <header className="flex items-start gap-2">
          <AlertTriangle
            size={16}
            strokeWidth={1.6}
            className={cn("mt-0.5 shrink-0", isOwner ? "text-signal-err" : "text-ink-mute")}
          />
          <div>
            <h3 className={cn("text-sm font-medium", isOwner ? "text-signal-err" : "text-ink")}>Danger zone</h3>
            <p className="mt-1 text-xs text-ink-dim">
              Soft-deletes the workspace. It disappears from your dashboard immediately and nested resources (workflows,
              agents) become inaccessible. Recovery requires an admin tool.
            </p>
          </div>
        </header>

        {!isOwner ? (
          <div className="mt-4 flex items-center gap-2">
            <Chip tone="default">owner-only</Chip>
            <span className="text-xs text-ink-mute">Only the workspace owner can delete it.</span>
          </div>
        ) : (
          <div className="mt-5 flex flex-col gap-3">
            <Field
              label="Type the workspace name to confirm"
              hint={
                <>
                  expected: <code className="font-mono text-ink-dim">{workspace?.name}</code>
                </>
              }
            >
              <Input
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder={workspace?.name}
                autoComplete="off"
                spellCheck={false}
              />
            </Field>

            {deleteWorkspace.error && (
              <p className="rounded-sm border border-signal-err/40 bg-signal-err/10 px-3 py-2 text-xs text-signal-err">
                {deleteWorkspace.error.message}
              </p>
            )}

            <div className="flex items-center justify-end">
              <Button
                type="button"
                variant="danger"
                onClick={onDelete}
                disabled={!canDelete || deleteWorkspace.isPending}
              >
                <Trash2 size={14} strokeWidth={1.8} />
                {deleteWorkspace.isPending ? "Deleting…" : "Delete workspace"}
              </Button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
