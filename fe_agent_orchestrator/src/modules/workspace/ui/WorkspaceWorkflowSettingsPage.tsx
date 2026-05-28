import { useMemo, useState } from "react";
import { Link, useParams } from "@tanstack/react-router";
import { ArrowLeft, Check, Copy, ListChecks, Plus, Trash2, TriangleAlert } from "lucide-react";

import {
  useCreateWebhook,
  useRevokeWebhook,
  useWebhooksForWorkflow,
  type WebhookCreated,
  type WebhookId,
  type WebhookSummary,
} from "@/entities/webhook";
import { useWorkflow, type Workflow, type WorkflowId } from "@/entities/workflow";
import type { WorkspaceId } from "@/entities/workspace";
import { Button, Chip, Field, Input, SectionHeader } from "@/shared/ui";

export function WorkspaceWorkflowSettingsPage() {
  const { workspaceId, workflowId } = useParams({
    from: "/protected/workspaces/$workspaceId/workflows/$workflowId/settings",
  });
  const wsId = workspaceId as WorkspaceId;
  const wfId = workflowId as WorkflowId;

  const { data: workflow } = useWorkflow(wsId, wfId);

  return (
    <div className="mx-auto w-full max-w-[860px] px-6 py-8">
      <Link
        to="/workspaces/$workspaceId/workflows/$workflowId"
        params={{ workspaceId: wsId, workflowId: wfId }}
        className="mb-4 inline-flex items-center gap-1.5 text-[11px] uppercase tracking-eyebrow text-ink-mute hover:text-ink"
      >
        <ArrowLeft size={12} strokeWidth={1.8} />
        back to workflow
      </Link>

      <SectionHeader
        title={workflow ? `${workflow.name} · Settings` : "Workflow settings"}
        meta={
          workflow ? (
            <code className="font-mono text-xs text-ink-mute">{workflow.slug}</code>
          ) : (
            "Loading…"
          )
        }
      />

      <div className="hairline-x mt-6" />

      <section className="mt-8">
        <WorkflowDetailsPanel workspaceId={wsId} workflowId={wfId} workflow={workflow ?? null} />
      </section>

      <section className="mt-8">
        <WebhooksPanel workspaceId={wsId} workflowId={wfId} />
      </section>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Workflow details — header card with id + counts + jump to logs
// ──────────────────────────────────────────────────────────────────────

function WorkflowDetailsPanel({
  workspaceId,
  workflowId,
  workflow,
}: {
  workspaceId: WorkspaceId;
  workflowId: WorkflowId;
  workflow: Workflow | null;
}) {
  // Node-type counts drive the headline stats. Read from the typed graph
  // (it's already loaded by the parent); fall back to compiledGraph when
  // graph happens to be empty (legacy rows).
  const counts = useMemo(() => countByType(workflow), [workflow]);
  const [copied, setCopied] = useState(false);

  const onCopyId = async () => {
    try {
      await navigator.clipboard.writeText(workflowId);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API gated on secure context — let the user select the
      // text by hand when permission is denied; nothing more to do safely.
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <header className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium text-ink">Workflow</h2>
          <p className="text-xs text-ink-dim">Identity, shape, status, and quick links.</p>
        </div>
        <Link
          to="/workspaces/$workspaceId/logs"
          params={{ workspaceId }}
          search={{ workflowId }}
          className="inline-flex items-center gap-1.5 rounded-md border border-canvas-rule bg-canvas-panel px-2.5 py-1 text-[11px] font-medium uppercase tracking-eyebrow text-ink-dim hover:border-sodium hover:text-sodium"
        >
          <ListChecks size={12} strokeWidth={1.8} />
          View logs
        </Link>
      </header>

      <div className="grid grid-cols-2 gap-3 rounded-md border border-canvas-rule bg-canvas-panel p-4 sm:grid-cols-4">
        <Stat label="Status" value={workflow?.status ?? "—"} valueIsChip workflow={workflow} />
        <Stat label="Agents" value={counts.agent} />
        <Stat label="Tools" value={counts.tool} />
        <Stat label="Conditions" value={counts.condition} />
        <Stat label="Nodes" value={counts.total} />
        <Stat label="Edges" value={counts.edges} />
        <Stat label="Created" value={workflow ? formatShort(workflow.createdAt) : "—"} />
        <Stat label="Updated" value={workflow ? formatShort(workflow.updatedAt) : "—"} />
      </div>

      <div className="flex flex-col gap-2 rounded-md border border-canvas-rule bg-canvas-panel p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-[10px] uppercase tracking-eyebrow text-ink-mute">Workflow ID</div>
            <code className="mt-0.5 block break-all font-mono text-xs text-ink">{workflowId}</code>
          </div>
          <button
            type="button"
            onClick={onCopyId}
            className="inline-flex items-center gap-1 rounded-md border border-canvas-rule px-2 py-1 text-[11px] font-medium text-ink-dim hover:border-sodium hover:text-sodium"
          >
            {copied ? <Check size={11} strokeWidth={1.8} /> : <Copy size={11} strokeWidth={1.8} />}
            {copied ? "copied" : "copy"}
          </button>
        </div>
        {workflow?.description && (
          <p className="border-t border-canvas-rule pt-2 text-xs leading-relaxed text-ink-dim">
            {workflow.description}
          </p>
        )}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  valueIsChip = false,
  workflow,
}: {
  label: string;
  value: string | number;
  valueIsChip?: boolean;
  workflow?: Workflow | null;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-eyebrow text-ink-mute">{label}</span>
      {valueIsChip && workflow ? (
        <Chip tone={workflow.status === "published" ? "ok" : "warn"}>{String(value)}</Chip>
      ) : (
        <span className="text-sm font-medium text-ink">{value}</span>
      )}
    </div>
  );
}

type NodeCounts = {
  agent: number;
  tool: number;
  condition: number;
  start: number;
  end: number;
  total: number;
  edges: number;
};

function countByType(workflow: Workflow | null): NodeCounts {
  const zero: NodeCounts = { agent: 0, tool: 0, condition: 0, start: 0, end: 0, total: 0, edges: 0 };
  if (!workflow) return zero;
  const counts = { ...zero };
  for (const node of workflow.graph.nodes) {
    counts.total += 1;
    if (node.type === "agent") counts.agent += 1;
    else if (node.type === "tool") counts.tool += 1;
    else if (node.type === "condition") counts.condition += 1;
    else if (node.type === "start") counts.start += 1;
    else if (node.type === "end") counts.end += 1;
  }
  counts.edges = workflow.graph.edges.length;
  return counts;
}

function formatShort(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

// ──────────────────────────────────────────────────────────────────────
// Webhooks panel
// ──────────────────────────────────────────────────────────────────────

function WebhooksPanel({ workspaceId, workflowId }: { workspaceId: WorkspaceId; workflowId: WorkflowId }) {
  const { data, isPending, error, refetch } = useWebhooksForWorkflow(workspaceId, workflowId);
  const create = useCreateWebhook(workspaceId, workflowId);

  // Plaintext token + URL shown once after a successful create. Kept in
  // local state only — never persisted, never read back from server.
  const [justCreated, setJustCreated] = useState<WebhookCreated | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);

  const onSubmit = async (e: { preventDefault: () => void }) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setNameError("Name is required.");
      return;
    }
    setNameError(null);
    const created = await create.mutateAsync({ name: trimmed });
    setJustCreated(created);
    setName("");
    setShowForm(false);
  };

  const items: WebhookSummary[] = data ?? [];
  const active = items.filter((w) => w.status === "active");
  const revoked = items.filter((w) => w.status === "revoked");

  return (
    <div className="flex flex-col gap-4">
      <header className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium text-ink">Webhooks</h2>
          <p className="text-xs text-ink-dim">
            Trigger this workflow from external integrations. Each token can be revoked independently.
          </p>
        </div>
        {!showForm && !justCreated && (
          <Button size="sm" onClick={() => setShowForm(true)}>
            <Plus size={14} strokeWidth={1.8} />
            New webhook
          </Button>
        )}
      </header>

      {justCreated && <FreshTokenCard created={justCreated} onDismiss={() => setJustCreated(null)} />}

      {showForm && (
        <form
          onSubmit={onSubmit}
          className="flex flex-col gap-3 rounded-md border border-canvas-rule bg-canvas-panel p-4"
        >
          <Field label="Name" required error={nameError ?? undefined} hint="Used to identify this token in the list.">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Production Slack"
              maxLength={120}
              autoFocus
            />
          </Field>
          {create.error && (
            <p className="rounded-md border border-signal-err/40 bg-signal-err/5 px-3 py-2 text-xs text-signal-err">
              {create.error.message}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setShowForm(false);
                setName("");
                setNameError(null);
              }}
            >
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={create.isPending}>
              {create.isPending ? "Generating…" : "Generate token"}
            </Button>
          </div>
        </form>
      )}

      {error && (
        <div className="flex items-center justify-between gap-2 rounded-md border border-signal-err/40 bg-signal-err/5 px-3 py-2 text-xs text-signal-err">
          <span>{error.message}</span>
          <button onClick={() => refetch()} className="underline">retry</button>
        </div>
      )}

      {isPending && (
        <div className="h-16 animate-pulse rounded-md border border-canvas-rule bg-canvas-panel/60" />
      )}

      {!isPending && active.length === 0 && !justCreated && (
        <p className="text-xs text-ink-mute">No webhooks yet. Generate one to wire up an integration.</p>
      )}

      {active.length > 0 && (
        <ul className="flex flex-col gap-2">
          {active.map((w) => (
            <WebhookRow key={w.id} workspaceId={workspaceId} workflowId={workflowId} webhook={w} />
          ))}
        </ul>
      )}

      {revoked.length > 0 && (
        <details className="rounded-md border border-canvas-rule bg-canvas-panel/40">
          <summary className="cursor-pointer px-3 py-2 text-[11px] uppercase tracking-eyebrow text-ink-mute">
            Revoked ({revoked.length})
          </summary>
          <ul className="flex flex-col gap-2 p-2">
            {revoked.map((w) => (
              <WebhookRow key={w.id} workspaceId={workspaceId} workflowId={workflowId} webhook={w} />
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// One-shot fresh-token card — shown exactly once after a successful POST
// ──────────────────────────────────────────────────────────────────────

function FreshTokenCard({ created, onDismiss }: { created: WebhookCreated; onDismiss: () => void }) {
  return (
    <div className="flex flex-col gap-3 rounded-md border border-sodium/60 bg-sodium-tint/60 p-4">
      <div className="flex items-start gap-2">
        <TriangleAlert size={16} strokeWidth={1.8} className="mt-0.5 shrink-0 text-sodium" />
        <div className="text-xs text-ink">
          <p className="font-medium text-ink">Copy this token now — you won't see it again.</p>
          <p className="mt-0.5 text-ink-dim">
            Once dismissed, only the prefix <code className="font-mono">{created.tokenPrefix}…</code> will be visible.
            Treat the token like an API key.
          </p>
        </div>
      </div>

      <CopyableField label="Token" value={created.token} mono />
      <CopyableField label="Webhook URL" value={created.url} mono />

      <div className="flex justify-end">
        <Button size="sm" onClick={onDismiss}>
          I copied it
        </Button>
      </div>
    </div>
  );
}

function CopyableField({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  const [copied, setCopied] = useState(false);
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API unavailable (insecure context, perm denied) — let the
      // user select the text manually; nothing more we can do safely.
    }
  };
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-eyebrow text-ink-mute">{label}</span>
      <div className="flex items-stretch gap-2">
        <code
          className={`flex-1 truncate rounded-md border border-canvas-rule bg-canvas px-2.5 py-1.5 text-xs text-ink ${
            mono ? "font-mono" : ""
          }`}
          title={value}
        >
          {value}
        </code>
        <button
          type="button"
          onClick={onCopy}
          aria-label={`Copy ${label.toLowerCase()}`}
          className="inline-flex items-center gap-1 rounded-md border border-canvas-rule bg-canvas-panel px-2.5 text-[11px] font-medium text-ink-dim hover:border-sodium hover:text-ink"
        >
          {copied ? <Check size={12} strokeWidth={1.8} /> : <Copy size={12} strokeWidth={1.8} />}
          {copied ? "copied" : "copy"}
        </button>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Existing-row card — prefix only, revoke button
// ──────────────────────────────────────────────────────────────────────

function WebhookRow({
  workspaceId,
  workflowId,
  webhook,
}: {
  workspaceId: WorkspaceId;
  workflowId: WorkflowId;
  webhook: WebhookSummary;
}) {
  const revoke = useRevokeWebhook(workspaceId, workflowId);
  const onRevoke = async () => {
    if (!confirm(`Revoke "${webhook.name}"? Any integration using this token will stop working.`)) return;
    await revoke.mutateAsync(webhook.id as WebhookId);
  };

  return (
    <li className="flex items-center justify-between gap-3 rounded-md border border-canvas-rule bg-canvas-panel px-3 py-2.5">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium text-ink">{webhook.name}</span>
          <Chip tone={webhook.status === "active" ? "ok" : "warn"}>{webhook.status}</Chip>
        </div>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-ink-mute">
          <code className="font-mono">{webhook.tokenPrefix}…</code>
          <span>created {formatDate(webhook.createdAt)}</span>
          {webhook.lastUsedAt ? (
            <span>last used {formatDate(webhook.lastUsedAt)}</span>
          ) : (
            <span>never used</span>
          )}
          {webhook.lastError && <span className="text-signal-err">last error: {webhook.lastError}</span>}
        </div>
      </div>
      {webhook.status === "active" && (
        <button
          type="button"
          onClick={onRevoke}
          disabled={revoke.isPending}
          aria-label={`Revoke ${webhook.name}`}
          title="Revoke"
          className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-canvas-rule text-ink-mute hover:border-signal-err hover:text-signal-err disabled:opacity-50"
        >
          <Trash2 size={13} strokeWidth={1.8} />
        </button>
      )}
    </li>
  );
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
