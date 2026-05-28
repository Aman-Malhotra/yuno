import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, AlertTriangle, KeyRound, Save, Settings2, Wrench } from "lucide-react";

import { Button, Chip, Field, Input, Select } from "@/shared/ui";
import {
  useAgentCapabilitiesForWorkspace,
  useCreateAgent,
  useUpdateAgent,
  type AgentDetail,
  type CreateAgentInput,
  type ProviderConfigField,
  type UpdateAgentInput,
} from "@/entities/agent";
import { ToolStatusChip, ToolTypeChip, useToolsInWorkspace } from "@/entities/tool";
import type { WorkspaceId } from "@/entities/workspace";
import { useWorkspaceLlmProviders } from "@/entities/workspace-llm-provider";
import { cn } from "@/shared/lib/cn";

import { createAgentSchema, type CreateAgentFormValues } from "../model/create-agent.form";

type Props = {
  workspaceId: WorkspaceId;
  /** Pass an existing agent to switch the form into edit mode (PATCH). */
  agent?: AgentDetail;
  onSuccess?: (agent: AgentDetail) => void;
  onCancel?: () => void;
};

function findConfigField(fields: ProviderConfigField[], key: string): ProviderConfigField | undefined {
  return fields.find((f) => f.key === key);
}

/** Serialise a JSONB blob for the form textarea. Empty objects render as
 * the canonical "{}" so users have something to anchor on. */
function prettyJson(value: Record<string, unknown> | undefined | null): string {
  if (!value || Object.keys(value).length === 0) return "{}";
  return JSON.stringify(value, null, 2);
}

/** Parse a form-supplied JSON string. Returns the parsed object, or the
 * raw error message in a tagged union so the caller can present it inline. */
function tryParseJsonObject(
  raw: string,
): { ok: true; value: Record<string, unknown> } | { ok: false; error: string } {
  const text = raw.trim();
  if (!text) return { ok: true, value: {} };
  try {
    const parsed: unknown = JSON.parse(text);
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      return { ok: false, error: "Must be a JSON object." };
    }
    return { ok: true, value: parsed as Record<string, unknown> };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Invalid JSON." };
  }
}

/** Reads `skills_config.tools[].name` (per ToolEntryShape) into a slug list. */
function readAttachedToolSlugs(skillsConfig: Record<string, unknown> | undefined): string[] {
  if (!skillsConfig) return [];
  const raw = skillsConfig.tools;
  if (!Array.isArray(raw)) return [];
  return raw
    .map((entry) => {
      if (entry && typeof entry === "object" && "name" in entry && typeof entry.name === "string") {
        return entry.name;
      }
      return null;
    })
    .filter((s): s is string => Boolean(s));
}

type CredentialSource = "workspace" | "byok";

export function CreateAgentForm({ workspaceId, agent, onSuccess, onCancel }: Props) {
  const isEdit = Boolean(agent);
  const caps = useAgentCapabilitiesForWorkspace(workspaceId);
  const workspaceCredentials = useWorkspaceLlmProviders(workspaceId);
  const tools = useToolsInWorkspace(workspaceId);

  const [credentialSource, setCredentialSource] = useState<CredentialSource>("workspace");

  const firstConfiguredProvider = useMemo(
    () => caps.data?.providers.find((p) => p.isConfigured) ?? caps.data?.providers[0],
    [caps.data],
  );

  const form = useForm<CreateAgentFormValues>({
    resolver: zodResolver(createAgentSchema),
    defaultValues: agent
      ? {
          name: agent.name,
          role: agent.role,
          systemPrompt: agent.systemPrompt,
          description: agent.description ?? "",
          modelProvider: agent.modelProvider,
          modelName: agent.modelName,
          temperature: agent.temperature,
          maxTokens: agent.maxTokens,
          providerApiKey: "",
          toolSlugs: readAttachedToolSlugs(agent.skillsConfig),
          maxToolHops:
            typeof agent.guardrailsConfig?.max_tool_hops === "number"
              ? (agent.guardrailsConfig.max_tool_hops as number)
              : undefined,
          memoryConfigJson: prettyJson(agent.memoryConfig),
          scheduleConfigJson: prettyJson(agent.scheduleConfig),
          guardrailsConfigJson: prettyJson(agent.guardrailsConfig),
          interactionRulesJson: prettyJson(agent.interactionRules),
          limitsConfigJson: prettyJson(agent.limitsConfig),
        }
      : {
          name: "",
          role: "",
          systemPrompt: "",
          description: "",
          modelProvider: "",
          modelName: "",
          temperature: 0.7,
          providerApiKey: "",
          toolSlugs: [],
          maxToolHops: undefined,
          memoryConfigJson: "{}",
          scheduleConfigJson: "{}",
          guardrailsConfigJson: "{}",
          interactionRulesJson: "{}",
          limitsConfigJson: "{}",
        },
  });

  // Seed provider + model from capabilities — create mode only. Edit mode
  // already has these from the agent's saved values.
  useEffect(() => {
    if (isEdit) return;
    if (!firstConfiguredProvider) return;
    if (form.getValues("modelProvider")) return;
    const defaultModel =
      firstConfiguredProvider.defaultModel ??
      firstConfiguredProvider.models.find((m) => m.isDefault)?.name ??
      firstConfiguredProvider.models[0]?.name ??
      "";
    const tempField = findConfigField(firstConfiguredProvider.configFields, "temperature");
    form.reset({
      ...form.getValues(),
      modelProvider: firstConfiguredProvider.key,
      modelName: defaultModel,
      temperature: typeof tempField?.default === "number" ? tempField.default : 0.7,
    });
  }, [isEdit, firstConfiguredProvider, form]);

  const selectedProviderKey = form.watch("modelProvider");
  const selectedProvider = useMemo(
    () => caps.data?.providers.find((p) => p.key === selectedProviderKey),
    [caps.data, selectedProviderKey],
  );

  const availableModels = selectedProvider?.models ?? [];

  // Keep model in sync when provider changes — only when user actively
  // switches providers, not on initial edit-mode load.
  useEffect(() => {
    if (!selectedProvider) return;
    const current = form.getValues("modelName");
    if (availableModels.some((m) => m.name === current)) return;
    const next =
      selectedProvider.defaultModel ?? availableModels.find((m) => m.isDefault)?.name ?? availableModels[0]?.name ?? "";
    form.setValue("modelName", next, { shouldValidate: true });
  }, [selectedProvider, availableModels, form]);

  // Clear API key on provider switch (provider-specific). Skip on first render
  // in edit mode so we don't blow away anything the user typed.
  useEffect(() => {
    form.setValue("providerApiKey", "");
  }, [selectedProviderKey, form]);

  const tempField = selectedProvider ? findConfigField(selectedProvider.configFields, "temperature") : undefined;
  const maxTokensField = selectedProvider ? findConfigField(selectedProvider.configFields, "max_tokens") : undefined;

  const createAgent = useCreateAgent(workspaceId);
  const updateAgent = useUpdateAgent(workspaceId, agent?.id ?? ("__noop__" as AgentDetail["id"]));

  // Workspace creds matching the currently-selected provider — these are
  // the candidates for the "use workspace default" path. If none exist,
  // the dropdown forces the user to BYOK an inline key.
  const matchingWorkspaceCreds = useMemo(
    () =>
      (workspaceCredentials.data ?? []).filter(
        (c) => c.provider === selectedProviderKey,
      ),
    [workspaceCredentials.data, selectedProviderKey],
  );

  // Auto-flip the dropdown to BYOK when the chosen provider has no
  // workspace default. Keeps the form honest about what will run.
  useEffect(() => {
    if (matchingWorkspaceCreds.length === 0 && credentialSource === "workspace") {
      setCredentialSource("byok");
    }
  }, [matchingWorkspaceCreds.length, credentialSource]);

  const selectedSlugs = form.watch("toolSlugs");
  const toggleTool = (slug: string) => {
    const current = form.getValues("toolSlugs") ?? [];
    const next = current.includes(slug) ? current.filter((s) => s !== slug) : [...current, slug];
    form.setValue("toolSlugs", next, { shouldDirty: true });
  };

  const onSubmit = form.handleSubmit(async (values) => {
    // Parse the five JSON config blocks. Surface parse errors per-field
    // and short-circuit submit so the bad blob doesn't blow up the PATCH.
    const memory = tryParseJsonObject(values.memoryConfigJson);
    const schedule = tryParseJsonObject(values.scheduleConfigJson);
    const guardrails = tryParseJsonObject(values.guardrailsConfigJson);
    const interactionRules = tryParseJsonObject(values.interactionRulesJson);
    const limits = tryParseJsonObject(values.limitsConfigJson);
    let parseFailed = false;
    if (!memory.ok) {
      form.setError("memoryConfigJson", { message: memory.error });
      parseFailed = true;
    }
    if (!schedule.ok) {
      form.setError("scheduleConfigJson", { message: schedule.error });
      parseFailed = true;
    }
    if (!guardrails.ok) {
      form.setError("guardrailsConfigJson", { message: guardrails.error });
      parseFailed = true;
    }
    if (!interactionRules.ok) {
      form.setError("interactionRulesJson", { message: interactionRules.error });
      parseFailed = true;
    }
    if (!limits.ok) {
      form.setError("limitsConfigJson", { message: limits.error });
      parseFailed = true;
    }
    if (parseFailed) return;

    // Merge the typed `maxToolHops` knob into guardrails so the typed
    // field always wins if both are set. The JSON textarea is the source
    // of truth for everything else.
    const guardrailsConfig =
      values.maxToolHops !== undefined && values.maxToolHops !== null
        ? { ...(guardrails as { ok: true; value: Record<string, unknown> }).value, max_tool_hops: values.maxToolHops }
        : (guardrails as { ok: true; value: Record<string, unknown> }).value;

    const runtimeConfigs = {
      memoryConfig: (memory as { ok: true; value: Record<string, unknown> }).value,
      scheduleConfig: (schedule as { ok: true; value: Record<string, unknown> }).value,
      guardrailsConfig,
      interactionRules: (interactionRules as { ok: true; value: Record<string, unknown> }).value,
      limitsConfig: (limits as { ok: true; value: Record<string, unknown> }).value,
    };

    // Credential handling: BYOK ships the key on the agent row;
    // workspace mode sends NO provider_credentials block so the backend
    // falls back to the workspace default at run time.
    const byokKey =
      credentialSource === "byok" ? values.providerApiKey?.trim() : undefined;
    const providerCredentials = byokKey ? { apiKey: byokKey } : undefined;

    const description = values.description?.trim() || undefined;

    if (isEdit && agent) {
      const patch: UpdateAgentInput = {
        name: values.name.trim(),
        role: values.role.trim(),
        systemPrompt: values.systemPrompt.trim(),
        modelProvider: values.modelProvider,
        modelName: values.modelName,
        description,
        temperature: values.temperature,
        maxTokens: values.maxTokens,
        toolSlugs: values.toolSlugs,
        providerCredentials,
        ...runtimeConfigs,
      };
      const updated = await updateAgent.mutateAsync(patch);
      onSuccess?.(updated);
      return;
    }

    const payload: CreateAgentInput = {
      name: values.name.trim(),
      role: values.role.trim(),
      systemPrompt: values.systemPrompt.trim(),
      modelProvider: values.modelProvider,
      modelName: values.modelName,
      description,
      temperature: values.temperature,
      maxTokens: values.maxTokens,
      toolSlugs: values.toolSlugs,
      providerCredentials,
      ...runtimeConfigs,
    };
    const created = await createAgent.mutateAsync(payload);
    form.reset();
    onSuccess?.(created);
  });

  if (caps.isPending) {
    return <p className="py-6 text-center text-xs text-ink-mute">Loading agent capabilities…</p>;
  }
  if (caps.isError) {
    return (
      <p className="rounded-sm border border-signal-err/40 bg-signal-err/5 px-3 py-2 text-xs text-signal-err">
        Couldn't load capabilities: {caps.error.message}
      </p>
    );
  }

  const providers = caps.data!.providers;
  const providerOptions = providers.map((p) => ({
    value: p.key,
    label: p.isConfigured ? p.displayName : `${p.displayName} · not configured`,
  }));
  const modelOptions = availableModels.map((m) => ({
    value: m.name,
    label: m.isDefault ? `${m.displayName} · default` : m.displayName,
  }));

  const providerNotConfigured = selectedProvider && !selectedProvider.isConfigured;
  const submitMutation = isEdit ? updateAgent : createAgent;
  const submitting = submitMutation.isPending;
  const availableTools = tools.data?.items ?? [];
  const workspaceCredForSelected = matchingWorkspaceCreds[0];

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-3" noValidate>
      <Field label="Name" required error={form.formState.errors.name?.message}>
        <Input placeholder="e.g. Support Router" maxLength={255} {...form.register("name")} />
      </Field>

      <Field
        label="Role"
        required
        hint="Short label, e.g. triage / researcher."
        error={form.formState.errors.role?.message}
      >
        <Input placeholder="triage" maxLength={120} {...form.register("role")} />
      </Field>

      <Field label="System prompt" required error={form.formState.errors.systemPrompt?.message}>
        <textarea
          rows={4}
          placeholder="You are a helpful…"
          className="min-h-[96px] w-full rounded-md border border-canvas-ruleStrong bg-canvas-panel px-3 py-2 text-sm text-ink placeholder:text-ink-mute focus-visible:border-sodium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sodium/40"
          {...form.register("systemPrompt")}
        />
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Provider" required error={form.formState.errors.modelProvider?.message}>
          <Select options={providerOptions} {...form.register("modelProvider")} />
        </Field>
        <Field
          label="Model"
          required
          hint={
            selectedProvider
              ? `${availableModels.length} models · ctx up to ${Math.max(
                  0,
                  ...availableModels.map((m) => m.contextWindow),
                ).toLocaleString()}`
              : undefined
          }
          error={form.formState.errors.modelName?.message}
        >
          <Select options={modelOptions} {...form.register("modelName")} />
        </Field>
      </div>

      {/* Credential source — workspace default vs per-agent BYOK */}
      <Field
        label={
          <span className="inline-flex items-center gap-1.5">
            <KeyRound size={11} strokeWidth={1.8} /> Credential source
          </span>
        }
        hint={
          matchingWorkspaceCreds.length > 0
            ? `${matchingWorkspaceCreds.length} workspace key${matchingWorkspaceCreds.length > 1 ? "s" : ""} available for ${selectedProvider?.displayName ?? "this provider"}.`
            : `No workspace key for ${selectedProvider?.displayName ?? "this provider"} — add one in LLM Providers, or paste a BYOK key below.`
        }
      >
        <Select
          options={[
            {
              value: "workspace",
              label:
                matchingWorkspaceCreds.length > 0
                  ? `Use workspace default${workspaceCredForSelected ? ` (${workspaceCredForSelected.last4})` : ""}`
                  : "Use workspace default · none configured",
            },
            { value: "byok", label: "BYOK · paste key inline" },
          ]}
          value={credentialSource}
          onChange={(e) => setCredentialSource(e.target.value as CredentialSource)}
        />
      </Field>

      {credentialSource === "byok" && (
        <Field
          label={
            <>
              <KeyRound size={11} strokeWidth={1.8} className="-mt-0.5 inline" />{" "}
              {selectedProvider?.displayName ?? "Provider"} API key
            </>
          }
          hint="Stored on the agent row (BYOK). The workspace default is not used for this agent's runs."
        >
          <Input
            type="password"
            placeholder="required when BYOK is selected"
            autoComplete="off"
            spellCheck={false}
            {...form.register("providerApiKey")}
          />
        </Field>
      )}

      {credentialSource === "workspace" && matchingWorkspaceCreds.length === 0 && (
        <div className="flex items-start gap-2 rounded-sm border border-sodium/40 bg-sodium-tint px-3 py-2 text-xs text-sodium">
          <AlertTriangle size={12} strokeWidth={2} className="mt-0.5 shrink-0" />
          <span>
            No workspace key for <strong>{selectedProvider?.displayName ?? "this provider"}</strong>. Add one in
            <em> LLM Providers</em>, or switch to BYOK and paste a key here.
          </span>
        </div>
      )}

      {providerNotConfigured && credentialSource === "workspace" && (
        <div className="flex items-start gap-2 rounded-sm border border-sodium/40 bg-sodium-tint px-3 py-2 text-xs text-sodium">
          <AlertTriangle size={12} strokeWidth={2} className="mt-0.5 shrink-0" />
          <span>
            <strong>{selectedProvider.displayName}</strong> isn't configured in this workspace. Agent will save but
            won't execute until a key is added.
          </span>
        </div>
      )}

      <Field label="Description" hint="Shown in the agent picker." error={form.formState.errors.description?.message}>
        <Input placeholder="optional" maxLength={2000} {...form.register("description")} />
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field
          label="Temperature"
          hint={tempField ? `${tempField.min ?? 0}–${tempField.max ?? 2} · ${tempField.description}` : "0.0–2.0"}
          error={form.formState.errors.temperature?.message}
        >
          <Input
            type="number"
            step="0.1"
            min={tempField?.min ?? 0}
            max={tempField?.max ?? 2}
            {...form.register("temperature", { valueAsNumber: true })}
          />
        </Field>
        <Field
          label="Max tokens"
          hint={
            maxTokensField
              ? `${maxTokensField.min ?? 1}–${(maxTokensField.max ?? 128_000).toLocaleString()} · optional`
              : "optional · 1–128k"
          }
          error={form.formState.errors.maxTokens?.message}
        >
          <Input
            type="number"
            min={maxTokensField?.min ?? 1}
            max={maxTokensField?.max ?? 128_000}
            {...form.register("maxTokens", { setValueAs: (v) => (v === "" ? undefined : Number(v)) })}
          />
        </Field>
      </div>

      <Field
        label={
          <span className="inline-flex items-center gap-1.5">
            <Wrench size={11} strokeWidth={1.8} /> Tools
          </span>
        }
        hint={
          availableTools.length === 0
            ? "No tools in this workspace yet — register one from the Tools tab."
            : `Select tools this agent can call. ${selectedSlugs.length} selected.`
        }
      >
        {tools.isPending ? (
          <p className="rounded-sm border border-canvas-rule bg-canvas-inset px-3 py-2 text-xs text-ink-mute">
            Loading tools…
          </p>
        ) : tools.isError ? (
          <p className="rounded-sm border border-signal-err/40 bg-signal-err/5 px-3 py-2 text-xs text-signal-err">
            Couldn't load tools: {tools.error.message}
          </p>
        ) : availableTools.length === 0 ? (
          <div className="rounded-sm border border-dashed border-canvas-rule bg-canvas-inset px-3 py-4 text-center text-xs text-ink-mute">
            No tools yet.
          </div>
        ) : (
          <ul className="flex max-h-[260px] flex-col divide-y divide-canvas-rule overflow-y-auto rounded-sm border border-canvas-rule bg-canvas-inset">
            {availableTools.map((tool) => {
              const checked = selectedSlugs.includes(tool.slug);
              return (
                <li key={tool.id}>
                  <button
                    type="button"
                    onClick={() => toggleTool(tool.slug)}
                    className={cn(
                      "flex w-full items-start gap-3 px-3 py-2.5 text-left transition-colors",
                      checked ? "bg-sodium-tint/60" : "hover:bg-canvas-panel",
                    )}
                  >
                    <span
                      aria-hidden
                      className={cn(
                        "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border transition-colors",
                        checked
                          ? "border-sodium bg-sodium text-canvas-panel"
                          : "border-canvas-ruleStrong bg-canvas-panel",
                      )}
                    >
                      {checked && (
                        <svg
                          width="10"
                          height="10"
                          viewBox="0 0 10 10"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <path d="M1 5l2.5 2.5L9 2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      )}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-xs font-medium text-ink">{tool.name}</span>
                        <code className="truncate font-mono text-[10px] text-ink-mute">{tool.slug}</code>
                      </div>
                      <p className="mt-0.5 line-clamp-1 text-[11px] text-ink-dim">{tool.description}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      <ToolTypeChip type={tool.type} />
                      <ToolStatusChip status={tool.status} />
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </Field>

      {caps.data!.tools.length === 0 && availableTools.length === 0 && (
        <div className="flex items-center gap-2 text-[11px] text-ink-mute">
          <Chip tone="default">tools</Chip>
          <span>No built-in or workspace tools yet — agent will run without tool calls.</span>
        </div>
      )}

      {/* ── Runtime configuration ─────────────────────────────────── */}
      <details className="rounded-md border border-canvas-rule bg-canvas-panel">
        <summary className="flex cursor-pointer items-center justify-between gap-2 px-3 py-2.5 text-xs font-medium text-ink">
          <span className="inline-flex items-center gap-1.5">
            <Settings2 size={12} strokeWidth={1.8} />
            Runtime configuration
          </span>
          <span className="text-[10px] uppercase tracking-eyebrow text-ink-mute">click to expand</span>
        </summary>
        <div className="flex flex-col gap-3 border-t border-canvas-rule p-3">
          <Field
            label="Max tool hops"
            hint="Cap on tool-call iterations inside ONE agent turn. Each iteration = 1 LLM call + N tool runs. Default 5. Bump if the agent runs out before completing; lower to fail fast on prompt loops."
            error={form.formState.errors.maxToolHops?.message}
          >
            <Input
              type="number"
              min={0}
              max={20}
              placeholder="5"
              {...form.register("maxToolHops", {
                setValueAs: (v) => (v === "" || v === null ? undefined : Number(v)),
              })}
            />
          </Field>

          <ConfigJsonField
            label="Guardrails config"
            hint="Approval gates, domain allow/block lists, rate limits. `max_tool_hops` here is overridden by the typed field above."
            name="guardrailsConfigJson"
            form={form}
          />
          <ConfigJsonField
            label="Limits config"
            hint="`max_input_tokens`, `max_output_tokens`, per-run cost caps."
            name="limitsConfigJson"
            form={form}
          />
          <ConfigJsonField
            label="Memory config"
            hint="Memory strategy + retention window (e.g. `{strategy: 'conversation', window: 20}`)."
            name="memoryConfigJson"
            form={form}
          />
          <ConfigJsonField
            label="Schedule config"
            hint="Cron / trigger windows for scheduled runs of this agent."
            name="scheduleConfigJson"
            form={form}
          />
          <ConfigJsonField
            label="Interaction rules"
            hint="Hand-off targets, emitted events, escalation rules (e.g. `{handoff_to: 'composer'}`)."
            name="interactionRulesJson"
            form={form}
          />
        </div>
      </details>

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
          {submitMutation.isPending
            ? isEdit
              ? "Saving…"
              : "Creating…"
            : isEdit
              ? "Save changes"
              : "Create agent"}
          {!submitting && (isEdit ? <Save size={14} strokeWidth={1.8} /> : <ArrowRight size={14} strokeWidth={1.8} />)}
        </Button>
      </div>
    </form>
  );
}

/** Monospace JSON textarea for one config block. Field-scoped error
 * surfaces parse failures inline so the user knows which block to fix. */
function ConfigJsonField({
  label,
  hint,
  name,
  form,
}: {
  label: string;
  hint: string;
  name:
    | "memoryConfigJson"
    | "scheduleConfigJson"
    | "guardrailsConfigJson"
    | "interactionRulesJson"
    | "limitsConfigJson";
  form: ReturnType<typeof useForm<CreateAgentFormValues>>;
}) {
  return (
    <Field label={label} hint={hint} error={form.formState.errors[name]?.message}>
      <textarea
        rows={4}
        spellCheck={false}
        className="min-h-[96px] w-full rounded-md border border-canvas-ruleStrong bg-canvas-panel px-3 py-2 font-mono text-[12px] text-ink placeholder:text-ink-mute focus-visible:border-sodium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sodium/40"
        placeholder="{}"
        {...form.register(name)}
      />
    </Field>
  );
}
