import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Save } from "lucide-react";

import { Button, Field, Input, Select } from "@/shared/ui";
import {
  useCreateTool,
  useUpdateTool,
  type CreateToolInput,
  type ToolDetail,
  type ToolStatus,
  type ToolType,
  type UpdateToolInput,
} from "@/entities/tool";
import type { WorkspaceId } from "@/entities/workspace";

import { createToolSchema, type CreateToolFormValues } from "../model/create-tool.form";

const TYPE_OPTIONS: { value: ToolType; label: string }[] = [
  { value: "builtin", label: "Built-in — wraps a registered handler" },
  { value: "http", label: "HTTP — REST integration" },
  { value: "messaging", label: "Messaging — Slack / WhatsApp / Telegram" },
  { value: "agent_handoff", label: "Agent handoff — call another agent" },
  { value: "webhook", label: "Webhook — outbound POST" },
  { value: "python", label: "Python — inline code snippet" },
  { value: "mock", label: "Mock — for testing only" },
];

const STATUS_OPTIONS: { value: ToolStatus; label: string }[] = [
  { value: "draft", label: "draft" },
  { value: "active", label: "active" },
  { value: "disabled", label: "disabled" },
  { value: "archived", label: "archived" },
];

const INPUT_SCHEMA_PLACEHOLDER = `{
  "type": "object",
  "properties": {
    "query": { "type": "string" }
  },
  "required": ["query"]
}`;

const OUTPUT_SCHEMA_PLACEHOLDER = `{
  "type": "object",
  "properties": {
    "result": { "type": "string" }
  }
}`;

const CONFIG_PLACEHOLDER = `{
  "url": "https://api.example.com/search",
  "method": "GET"
}`;

type Props = {
  workspaceId: WorkspaceId;
  /** Pass an existing tool to switch the form into edit mode (PATCH). */
  tool?: ToolDetail;
  onSuccess?: (tool: ToolDetail) => void;
  onCancel?: () => void;
};

function parseJsonObjectOrUndefined(raw: string | undefined): Record<string, unknown> | undefined {
  if (!raw || !raw.trim()) return undefined;
  return JSON.parse(raw) as Record<string, unknown>;
}

/** Pretty-print a JSON blob for the textarea; empty objects render as ""
 * so the placeholder shows through. */
function jsonForTextarea(value: Record<string, unknown> | undefined): string {
  if (!value || Object.keys(value).length === 0) return "";
  return JSON.stringify(value, null, 2);
}

export function CreateToolForm({ workspaceId, tool, onSuccess, onCancel }: Props) {
  const isEdit = Boolean(tool);

  const form = useForm<CreateToolFormValues>({
    resolver: zodResolver(createToolSchema),
    defaultValues: tool
      ? {
          name: tool.name,
          description: tool.description,
          type: tool.type,
          category: tool.category,
          icon: tool.icon ?? "",
          status: tool.status,
          inputSchemaRaw: jsonForTextarea(tool.inputSchema),
          outputSchemaRaw: jsonForTextarea(tool.outputSchema),
          configRaw: jsonForTextarea(tool.config),
          publishNewVersion: false,
        }
      : {
          name: "",
          description: "",
          type: "http",
          category: "general",
          icon: "",
          status: "draft",
          inputSchemaRaw: "",
          outputSchemaRaw: "",
          configRaw: "",
          publishNewVersion: false,
        },
  });

  const createTool = useCreateTool(workspaceId);
  const updateTool = useUpdateTool(workspaceId, tool?.id ?? ("__noop__" as ToolDetail["id"]));
  const selectedType = form.watch("type");

  const onSubmit = form.handleSubmit(async (values) => {
    if (isEdit && tool) {
      const patch: UpdateToolInput = {
        name: values.name.trim(),
        description: values.description.trim(),
        category: values.category?.trim() || undefined,
        icon: values.icon?.trim() || undefined,
        status: values.status,
        inputSchema: parseJsonObjectOrUndefined(values.inputSchemaRaw) ?? {},
        outputSchema: parseJsonObjectOrUndefined(values.outputSchemaRaw) ?? {},
        config: parseJsonObjectOrUndefined(values.configRaw) ?? {},
        publishNewVersion: values.publishNewVersion,
      };
      const updated = await updateTool.mutateAsync(patch);
      onSuccess?.(updated);
      return;
    }

    const payload: CreateToolInput = {
      name: values.name.trim(),
      description: values.description.trim(),
      type: values.type,
      category: values.category?.trim() || undefined,
      icon: values.icon?.trim() || undefined,
      status: values.status,
      inputSchema: parseJsonObjectOrUndefined(values.inputSchemaRaw),
      outputSchema: parseJsonObjectOrUndefined(values.outputSchemaRaw),
      config: parseJsonObjectOrUndefined(values.configRaw),
    };
    const created = await createTool.mutateAsync(payload);
    form.reset();
    onSuccess?.(created);
  });

  const submitMutation = isEdit ? updateTool : createTool;
  const submitting = submitMutation.isPending;

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-3" noValidate>
      <div className="grid grid-cols-2 gap-3">
        <Field
          label="Name"
          required
          hint="The display name. Slug is derived server-side."
          error={form.formState.errors.name?.message}
        >
          <Input placeholder="Send Slack message" maxLength={255} autoComplete="off" {...form.register("name")} />
        </Field>
        <Field
          label="Type"
          required
          hint={isEdit ? "Type is immutable after creation." : undefined}
          error={form.formState.errors.type?.message}
        >
          <Select options={TYPE_OPTIONS} disabled={isEdit} {...form.register("type")} />
        </Field>
      </div>

      <Field
        label="Description"
        required
        hint="LLM-facing docstring — be specific about when the tool should be called."
        error={form.formState.errors.description?.message}
      >
        <textarea
          rows={3}
          placeholder="Send a message to a Slack channel. Use whenever a human needs to be notified."
          className="min-h-[72px] w-full rounded-md border border-canvas-ruleStrong bg-canvas-panel px-3 py-2 text-sm text-ink placeholder:text-ink-mute focus-visible:border-sodium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sodium/40"
          {...form.register("description")}
        />
      </Field>

      <div className="grid grid-cols-3 gap-3">
        <Field label="Category" hint="default: general" error={form.formState.errors.category?.message}>
          <Input placeholder="communication" maxLength={64} autoComplete="off" {...form.register("category")} />
        </Field>
        <Field label="Icon" hint="lucide-react name (optional)" error={form.formState.errors.icon?.message}>
          <Input placeholder="slack" maxLength={120} autoComplete="off" {...form.register("icon")} />
        </Field>
        <Field label="Status" error={form.formState.errors.status?.message}>
          <Select options={STATUS_OPTIONS} {...form.register("status")} />
        </Field>
      </div>

      <Field
        label="Input schema"
        hint="JSON Schema (Draft-07) for the tool's input. Optional."
        error={form.formState.errors.inputSchemaRaw?.message}
      >
        <textarea
          rows={6}
          spellCheck={false}
          placeholder={INPUT_SCHEMA_PLACEHOLDER}
          className="min-h-[150px] w-full rounded-md border border-canvas-ruleStrong bg-canvas-inset px-3 py-2 font-mono text-[12px] leading-relaxed text-ink placeholder:text-ink-mute focus-visible:border-sodium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sodium/40"
          {...form.register("inputSchemaRaw")}
        />
      </Field>

      <Field
        label="Output schema"
        hint="JSON Schema describing the tool's return shape. Optional."
        error={form.formState.errors.outputSchemaRaw?.message}
      >
        <textarea
          rows={5}
          spellCheck={false}
          placeholder={OUTPUT_SCHEMA_PLACEHOLDER}
          className="min-h-[120px] w-full rounded-md border border-canvas-ruleStrong bg-canvas-inset px-3 py-2 font-mono text-[12px] leading-relaxed text-ink placeholder:text-ink-mute focus-visible:border-sodium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sodium/40"
          {...form.register("outputSchemaRaw")}
        />
      </Field>

      <Field
        label="Config"
        hint={`Per-type executor config — shape depends on type=${selectedType}. Edit later from the detail page if you skip this.`}
        error={form.formState.errors.configRaw?.message}
      >
        <textarea
          rows={5}
          spellCheck={false}
          placeholder={CONFIG_PLACEHOLDER}
          className="min-h-[120px] w-full rounded-md border border-canvas-ruleStrong bg-canvas-inset px-3 py-2 font-mono text-[12px] leading-relaxed text-ink placeholder:text-ink-mute focus-visible:border-sodium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sodium/40"
          {...form.register("configRaw")}
        />
      </Field>

      {isEdit ? (
        <label className="flex items-start gap-2 rounded-sm border border-canvas-rule bg-canvas-inset px-3 py-2 text-[11px] text-ink-dim">
          <input type="checkbox" className="mt-0.5 h-3.5 w-3.5 accent-sodium" {...form.register("publishNewVersion")} />
          <span>
            Publish a new version after saving. Snapshots the current schema + config so workflow runs pinned to v
            {tool!.version} keep their behaviour.
          </span>
        </label>
      ) : (
        <p className="text-[11px] text-ink-mute">
          Auth, guardrails, execution-policy and channels can be set after creation via the detail page.
        </p>
      )}

      {submitMutation.error && (
        <p className="rounded-sm border border-signal-err/40 bg-signal-err/5 px-3 py-2 text-xs text-signal-err">
          {submitMutation.error.message}
        </p>
      )}

      <div className="flex items-center justify-end gap-2 pt-1">
        {onCancel && (
          <Button type="button" variant="ghost" onClick={onCancel} disabled={submitting}>
            Cancel
          </Button>
        )}
        <Button type="submit" disabled={submitting}>
          {submitting ? (isEdit ? "Saving…" : "Registering…") : isEdit ? "Save changes" : "Register tool"}
          {!submitting && (isEdit ? <Save size={14} strokeWidth={1.8} /> : <ArrowRight size={14} strokeWidth={1.8} />)}
        </Button>
      </div>
    </form>
  );
}
