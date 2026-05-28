import { useEffect, useMemo, useState } from "react";
import { useParams } from "@tanstack/react-router";
import { KeyRound, Loader2, Plus, Trash2 } from "lucide-react";

import { useAgentCapabilities } from "@/entities/agent";
import {
  type WorkspaceCredentialId,
  type WorkspaceCredentialSummary,
  useCreateWorkspaceLlmProvider,
  useDeleteWorkspaceLlmProvider,
  useWorkspaceLlmProviders,
} from "@/entities/workspace-llm-provider";
import type { WorkspaceId } from "@/entities/workspace";
import { Button, Chip, SectionHeader } from "@/shared/ui";

export function WorkspaceLLMProvidersPage() {
  const { workspaceId } = useParams({ from: "/protected/workspaces/$workspaceId" });
  const wsId = workspaceId as WorkspaceId;

  const credentials = useWorkspaceLlmProviders(wsId);
  const capabilities = useAgentCapabilities();
  const createMut = useCreateWorkspaceLlmProvider(wsId);
  const deleteMut = useDeleteWorkspaceLlmProvider(wsId);

  const providerOptions = useMemo(
    () => (capabilities.data?.providers ?? []).map((p) => ({ key: p.key, label: p.displayName })),
    [capabilities.data?.providers],
  );

  return (
    <div className="mx-auto w-full max-w-[1180px] px-6 py-8">
      <SectionHeader
        title="LLM Providers"
        meta="Workspace-default API keys. Every agent in this workspace falls back to these when it has no per-agent BYOK key."
        right={credentials.data ? <Chip tone="default">{credentials.data.length} configured</Chip> : null}
      />

      <div className="hairline-x mt-6" />

      <AddProviderForm
        providerOptions={providerOptions}
        existingProviders={new Set((credentials.data ?? []).map((c) => c.provider))}
        isSubmitting={createMut.isPending}
        errorMessage={createMut.error?.message}
        onSubmit={(input) => createMut.mutate(input, { onSuccess: () => createMut.reset() })}
      />

      <section className="mt-8">
        {credentials.isError && (
          <div className="mb-4 rounded-md border border-signal-err/40 bg-signal-err/5 p-4 text-sm text-signal-err">
            {credentials.error?.message ?? "Couldn't load credentials."}
          </div>
        )}

        {credentials.isPending && !credentials.data ? (
          <div className="space-y-2">
            {Array.from({ length: 2 }).map((_, i) => (
              <div
                key={i}
                aria-hidden
                className="h-[72px] animate-pulse rounded-md border border-canvas-rule bg-canvas-panel/60"
              />
            ))}
          </div>
        ) : (credentials.data ?? []).length === 0 ? (
          <div className="rounded-md border border-canvas-rule bg-canvas-panel/40 p-6 text-center text-sm text-ink-mute">
            No workspace credentials yet. Add one above so agents can share a default key.
          </div>
        ) : (
          <ul className="space-y-2">
            {credentials.data!.map((cred) => (
              <CredentialRow
                key={cred.id}
                credential={cred}
                onDelete={(id) => deleteMut.mutate(id)}
                isDeleting={deleteMut.isPending && deleteMut.variables === cred.id}
              />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────── */

function AddProviderForm({
  providerOptions,
  existingProviders,
  isSubmitting,
  errorMessage,
  onSubmit,
}: {
  providerOptions: { key: string; label: string }[];
  existingProviders: Set<string>;
  isSubmitting: boolean;
  errorMessage?: string;
  onSubmit: (input: {
    provider: string;
    apiKey: string;
    baseUrl?: string;
    organization?: string;
  }) => void;
}) {
  const [provider, setProvider] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [organization, setOrganization] = useState("");

  // Sync default provider when options arrive. Capabilities loads async,
  // so the initial useState("") would otherwise stick and the Save button
  // would stay disabled even though the <select> visually shows an option.
  useEffect(() => {
    if (provider) return;
    const fallback = providerOptions[0]?.key;
    if (!fallback) return;
    const firstAvailable =
      providerOptions.find((p) => !existingProviders.has(p.key))?.key ?? fallback;
    setProvider(firstAvailable);
  }, [provider, providerOptions, existingProviders]);

  const submit = () => {
    if (!provider || !apiKey.trim()) return;
    onSubmit({
      provider,
      apiKey: apiKey.trim(),
      baseUrl: baseUrl.trim() || undefined,
      organization: organization.trim() || undefined,
    });
    setApiKey("");
    setBaseUrl("");
    setOrganization("");
  };

  return (
    <div className="mt-5 rounded-md border border-canvas-rule bg-canvas-panel p-4">
      <div className="mb-3 flex items-center gap-2">
        <KeyRound size={14} strokeWidth={1.6} className="text-sodium" />
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-faint">
          Add credential
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1">
          <span className="text-[11px] text-ink-mute">Provider</span>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="rounded-sm border border-canvas-rule bg-canvas-inset px-3 py-1.5 text-[13px] text-ink focus:border-sodium focus:outline-none"
          >
            {providerOptions.length === 0 && <option value="">Loading…</option>}
            {providerOptions.map((p) => (
              <option key={p.key} value={p.key}>
                {p.label}
                {existingProviders.has(p.key) ? " (will replace)" : ""}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-[11px] text-ink-mute">API key</span>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="sk-... / gsk_... / AIza..."
            className="rounded-sm border border-canvas-rule bg-canvas-inset px-3 py-1.5 font-mono text-[12px] text-ink focus:border-sodium focus:outline-none"
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-[11px] text-ink-mute">
            Base URL <span className="text-ink-faint">(optional)</span>
          </span>
          <input
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="https://api.groq.com/openai/v1"
            className="rounded-sm border border-canvas-rule bg-canvas-inset px-3 py-1.5 text-[13px] text-ink focus:border-sodium focus:outline-none"
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-[11px] text-ink-mute">
            Organization <span className="text-ink-faint">(OpenAI only)</span>
          </span>
          <input
            value={organization}
            onChange={(e) => setOrganization(e.target.value)}
            className="rounded-sm border border-canvas-rule bg-canvas-inset px-3 py-1.5 text-[13px] text-ink focus:border-sodium focus:outline-none"
          />
        </label>
      </div>

      {errorMessage && (
        <p className="mt-2 text-[12px] text-signal-err">{errorMessage}</p>
      )}

      <div className="mt-3 flex justify-end">
        <Button
          type="button"
          onClick={submit}
          disabled={isSubmitting || !provider || !apiKey.trim()}
        >
          {isSubmitting ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
          {isSubmitting ? "Saving…" : "Save"}
        </Button>
      </div>
    </div>
  );
}

function CredentialRow({
  credential,
  onDelete,
  isDeleting,
}: {
  credential: WorkspaceCredentialSummary;
  onDelete: (id: WorkspaceCredentialId) => void;
  isDeleting: boolean;
}) {
  return (
    <li className="flex items-start gap-3 rounded-md border border-canvas-rule bg-canvas-panel px-4 py-3">
      <div className="mt-0.5 text-ink-mute">
        <KeyRound size={14} strokeWidth={1.6} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-medium text-ink">{credential.provider}</span>
          <span className="font-mono text-[10px] text-ink-mute">{credential.last4}</span>
        </div>
        <div className="mt-0.5 flex flex-wrap gap-3 text-[10px] text-ink-mute">
          {credential.baseUrl && (
            <span>
              base: <span className="font-mono">{credential.baseUrl}</span>
            </span>
          )}
          {credential.organization && (
            <span>
              org: <span className="font-mono">{credential.organization}</span>
            </span>
          )}
          <span className="font-mono">updated {credential.updatedAt}</span>
        </div>
      </div>
      <button
        type="button"
        onClick={() => onDelete(credential.id)}
        disabled={isDeleting}
        className="inline-flex h-7 w-7 items-center justify-center rounded-sm text-ink-mute transition-colors hover:bg-canvas-inset hover:text-signal-err disabled:opacity-40"
        title="Delete credential"
      >
        <Trash2 size={14} strokeWidth={1.6} />
      </button>
    </li>
  );
}
