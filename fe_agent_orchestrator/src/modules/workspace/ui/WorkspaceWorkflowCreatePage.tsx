import { useState } from "react";
import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { ArrowLeft, ArrowRight } from "lucide-react";

import { useCreateWorkflow } from "@/entities/workflow";
import type { WorkspaceId } from "@/entities/workspace";
import { Button, Field, Input, SectionHeader } from "@/shared/ui";

/**
 * Lightweight create step. Collect a name (and optional description),
 * POST `/workspaces/{ws}/workflows/` to materialize the row, then redirect
 * straight into the builder canvas at the detail route — autosave takes
 * over from there.
 *
 * Keeping create simple (no canvas here) means we never have to reconcile
 * unsaved local state with a freshly-created server row.
 */
export function WorkspaceWorkflowCreatePage() {
  const { workspaceId } = useParams({ from: "/protected/workspaces/$workspaceId" });
  const wsId = workspaceId as WorkspaceId;
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);

  const createWorkflow = useCreateWorkflow(wsId);

  const onSubmit = async (e: { preventDefault: () => void }) => {
    e.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) {
      setNameError("Workflow needs a name.");
      return;
    }
    setNameError(null);
    const created = await createWorkflow.mutateAsync({
      name: trimmedName,
      description: description.trim() || undefined,
    });
    navigate({
      to: "/workspaces/$workspaceId/workflows/$workflowId",
      params: { workspaceId: wsId, workflowId: created.id },
    });
  };

  return (
    <div className="mx-auto w-full max-w-[640px] px-6 py-8">
      <Link
        to="/workspaces/$workspaceId/workflows"
        params={{ workspaceId: wsId }}
        className="mb-4 inline-flex items-center gap-1.5 text-[11px] uppercase tracking-eyebrow text-ink-mute hover:text-ink"
      >
        <ArrowLeft size={12} strokeWidth={1.8} />
        all workflows
      </Link>

      <SectionHeader title="New workflow" meta="Name it. You'll wire agents on the next screen." />

      <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-4">
        <Field label="Name" required error={nameError ?? undefined}>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Inbound triage"
            maxLength={255}
            autoFocus
          />
        </Field>

        <Field label="Description" hint="Optional — shown on the workflow card.">
          <Input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Routes inbound questions to the right specialist."
            maxLength={4000}
          />
        </Field>

        {createWorkflow.error && (
          <p className="rounded-md border border-signal-err/40 bg-signal-err/5 px-3 py-2 text-xs text-signal-err">
            {createWorkflow.error.message}
          </p>
        )}

        <div className="flex justify-end pt-2">
          <Button type="submit" disabled={createWorkflow.isPending}>
            {createWorkflow.isPending ? "Creating…" : "Open builder"}
            {!createWorkflow.isPending && <ArrowRight size={14} strokeWidth={1.8} />}
          </Button>
        </div>
      </form>
    </div>
  );
}
