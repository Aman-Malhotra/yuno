import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight } from "lucide-react";

import { Button, Field, Input } from "@/shared/ui";
import { useCreateWorkspace, type WorkspaceSummary } from "@/entities/workspace";

import { createWorkspaceSchema, type CreateWorkspaceInput } from "../model/create-workspace.form";

type Props = {
  onSuccess?: (workspace: WorkspaceSummary) => void;
  onCancel?: () => void;
};

export function CreateWorkspaceForm({ onSuccess, onCancel }: Props) {
  const form = useForm<CreateWorkspaceInput>({
    resolver: zodResolver(createWorkspaceSchema),
    defaultValues: { name: "" },
  });

  const createWorkspace = useCreateWorkspace();

  const onSubmit = form.handleSubmit(async (input) => {
    const ws = await createWorkspace.mutateAsync(input);
    form.reset();
    onSuccess?.(ws);
  });

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
      <Field
        label="Workspace name"
        required
        hint="Slug is generated server-side from the name."
        error={form.formState.errors.name?.message}
      >
        <Input
          autoFocus
          autoComplete="off"
          placeholder="e.g. Acme Engineering"
          maxLength={255}
          {...form.register("name")}
        />
      </Field>

      {createWorkspace.error && (
        <p className="rounded-sm border border-signal-err/40 bg-signal-err/5 px-3 py-2 text-xs text-signal-err">
          {createWorkspace.error.message}
        </p>
      )}

      <div className="flex items-center justify-end gap-2 pt-1">
        {onCancel && (
          <Button type="button" variant="ghost" onClick={onCancel} disabled={createWorkspace.isPending}>
            Cancel
          </Button>
        )}
        <Button type="submit" disabled={createWorkspace.isPending}>
          {createWorkspace.isPending ? "Creating…" : "Create workspace"}
          {!createWorkspace.isPending && <ArrowRight size={14} strokeWidth={1.8} />}
        </Button>
      </div>
    </form>
  );
}
