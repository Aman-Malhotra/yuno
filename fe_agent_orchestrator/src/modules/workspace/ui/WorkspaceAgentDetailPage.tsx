import { Link, useParams } from "@tanstack/react-router";
import { ArrowLeft, ArrowUpRight, KeyRound, Pencil, Wrench } from "lucide-react";

import { useAgent, type AgentId, type AgentStatus } from "@/entities/agent";
import { ToolStatusChip, ToolTypeChip, useToolsInWorkspace, type ToolSummary } from "@/entities/tool";
import type { WorkspaceId } from "@/entities/workspace";
import { Chip, SectionHeader } from "@/shared/ui";
import { cn } from "@/shared/lib/cn";

function formatDateTime(iso: string): string {
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

const statusTone: Record<AgentStatus, "ok" | "warn" | "default"> = {
  active: "ok",
  draft: "warn",
  archived: "default",
};

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[160px_1fr] items-baseline gap-4 border-b border-canvas-rule py-3 last:border-b-0">
      <dt className="eyebrow">{label}</dt>
      <dd className="text-sm text-ink">{value}</dd>
    </div>
  );
}

function ConfigBlock({ label, value }: { label: string; value: Record<string, unknown> }) {
  const isEmpty = !value || Object.keys(value).length === 0;
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="eyebrow">{label}</span>
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-faint">
          {isEmpty ? "empty" : `${Object.keys(value).length} keys`}
        </span>
      </div>
      <pre
        className={cn(
          "overflow-x-auto rounded-sm border border-canvas-rule bg-canvas-inset px-3 py-2 font-mono text-[11px] leading-relaxed",
          isEmpty ? "text-ink-faint" : "text-ink-dim",
        )}
      >
        {isEmpty ? "{}" : JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}

/**
 * Pulls the tool entries out of `agent.skills_config.tools` per the spec's
 * ToolEntryShape — each entry has a `name` (matches a tool's slug) and an
 * `options` blob. Returns just the slugs in order.
 */
function readAttachedToolSlugs(skillsConfig: Record<string, unknown>): string[] {
  const raw = skillsConfig?.tools;
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

type AttachedTool = { slug: string; tool: ToolSummary; resolved: true } | { slug: string; tool: null; resolved: false };

function AttachedToolRow({ attached, workspaceId }: { attached: AttachedTool; workspaceId: WorkspaceId }) {
  if (!attached.resolved) {
    return (
      <li
        className="flex items-center justify-between gap-3 rounded-sm border border-dashed border-canvas-ruleStrong bg-canvas-inset/60 px-3 py-2.5"
        title="Tool no longer exists in this workspace."
      >
        <div className="flex min-w-0 items-center gap-2">
          <Wrench size={14} strokeWidth={1.6} className="shrink-0 text-ink-faint" />
          <code className="truncate font-mono text-xs text-ink-mute">{attached.slug}</code>
          <Chip tone="warn">unresolved</Chip>
        </div>
      </li>
    );
  }

  const { tool } = attached;
  return (
    <li>
      <Link
        to="/workspaces/$workspaceId/tools/$toolId"
        params={{ workspaceId, toolId: tool.id }}
        className="group flex items-center justify-between gap-3 rounded-sm border border-canvas-rule bg-canvas-panel px-3 py-2.5 transition-colors hover:border-sodium"
      >
        <div className="flex min-w-0 items-center gap-3">
          <span
            aria-hidden
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-sm border border-canvas-ruleStrong bg-canvas-inset text-ink-mute group-hover:text-sodium"
          >
            <Wrench size={13} strokeWidth={1.6} />
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="truncate text-xs font-medium text-ink">{tool.name}</span>
              <code className="truncate font-mono text-[10px] text-ink-mute">{tool.slug}</code>
            </div>
            <p className="mt-0.5 line-clamp-1 text-[11px] text-ink-dim">{tool.description}</p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <ToolTypeChip type={tool.type} />
          <ToolStatusChip status={tool.status} />
          <ArrowUpRight size={14} strokeWidth={1.6} className="text-ink-mute group-hover:text-sodium" />
        </div>
      </Link>
    </li>
  );
}

export function WorkspaceAgentDetailPage() {
  const { workspaceId, agentId } = useParams({ from: "/protected/workspaces/$workspaceId/agents/$agentId" });
  const wsId = workspaceId as WorkspaceId;
  const aId = agentId as AgentId;

  const agent = useAgent(wsId, aId);
  const tools = useToolsInWorkspace(wsId);

  const attachedSlugs = agent.data ? readAttachedToolSlugs(agent.data.skillsConfig) : [];
  const attached: AttachedTool[] = attachedSlugs.map((slug) => {
    const tool = tools.data?.items.find((t) => t.slug === slug);
    return tool ? { slug, tool, resolved: true } : { slug, tool: null, resolved: false };
  });

  return (
    <div className="mx-auto w-full max-w-[1180px] px-6 py-8">
      <Link
        to="/workspaces/$workspaceId/agents"
        params={{ workspaceId: wsId }}
        className="mb-4 inline-flex items-center gap-1.5 text-[11px] uppercase tracking-eyebrow text-ink-mute hover:text-ink"
      >
        <ArrowLeft size={12} strokeWidth={1.8} />
        all agents
      </Link>

      {agent.isPending && <p className="text-sm text-ink-mute">Loading agent…</p>}
      {agent.isError && (
        <div className="rounded-md border border-signal-err/40 bg-signal-err/5 p-4 text-sm text-signal-err">
          {agent.error.message}
        </div>
      )}

      {agent.data && (
        <>
          <SectionHeader
            title={agent.data.name}
            meta={
              <span className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-ink-dim">{agent.data.role}</span>
                <span className="text-ink-faint">·</span>
                <code className="font-mono text-xs text-ink-mute">{agent.data.slug}</code>
              </span>
            }
            right={
              <div className="flex items-center gap-2">
                <Chip tone={statusTone[agent.data.status]}>{agent.data.status}</Chip>
                {agent.data.providerCredentialsConfigured && (
                  <Chip tone="accent" icon={<KeyRound size={10} strokeWidth={2} />}>
                    byok
                  </Chip>
                )}
                <Link
                  to="/workspaces/$workspaceId/agents/$agentId/edit"
                  params={{ workspaceId: wsId, agentId: agent.data.id }}
                  className="inline-flex h-7 items-center gap-1.5 rounded-md border border-canvas-ruleStrong bg-canvas-panel px-2.5 text-xs font-medium text-ink transition-colors hover:border-sodium hover:text-sodium"
                >
                  <Pencil size={12} strokeWidth={1.8} />
                  Edit
                </Link>
              </div>
            }
          />

          <div className="hairline-x mt-6" />

          {/* Identity */}
          <section className="mt-6 rounded-md border border-canvas-rule bg-canvas-panel p-6">
            <h3 className="text-sm font-medium text-ink">Identity</h3>
            <dl className="mt-4">
              <DetailRow label="Name" value={agent.data.name} />
              <DetailRow label="Role" value={<span className="font-mono">{agent.data.role}</span>} />
              <DetailRow
                label="Slug"
                value={<code className="font-mono text-xs text-ink-dim">{agent.data.slug}</code>}
              />
              <DetailRow
                label="Description"
                value={agent.data.description ?? <span className="text-ink-mute">—</span>}
              />
              <DetailRow
                label="Agent ID"
                value={<code className="font-mono text-xs text-ink-dim">{agent.data.id}</code>}
              />
              <DetailRow
                label="Workspace ID"
                value={<code className="font-mono text-xs text-ink-dim">{agent.data.workspaceId}</code>}
              />
            </dl>
          </section>

          {/* Model */}
          <section className="mt-6 rounded-md border border-canvas-rule bg-canvas-panel p-6">
            <h3 className="text-sm font-medium text-ink">Model</h3>
            <dl className="mt-4">
              <DetailRow label="Provider" value={<span className="font-mono">{agent.data.modelProvider}</span>} />
              <DetailRow label="Model" value={<span className="font-mono">{agent.data.modelName}</span>} />
              <DetailRow label="Temperature" value={<span className="tabular-nums">{agent.data.temperature}</span>} />
              <DetailRow
                label="Max tokens"
                value={
                  agent.data.maxTokens != null ? (
                    <span className="tabular-nums">{agent.data.maxTokens.toLocaleString()}</span>
                  ) : (
                    <span className="text-ink-mute">— (provider default)</span>
                  )
                }
              />
              <DetailRow
                label="Top-p"
                value={
                  agent.data.topP != null ? (
                    <span className="tabular-nums">{agent.data.topP}</span>
                  ) : (
                    <span className="text-ink-mute">— (provider default)</span>
                  )
                }
              />
              <DetailRow
                label="Per-agent key"
                value={
                  agent.data.providerCredentialsConfigured ? (
                    <span className="text-signal-ok">configured (BYOK override)</span>
                  ) : (
                    <span className="text-ink-mute">— using workspace/server key</span>
                  )
                }
              />
            </dl>
          </section>

          {/* System prompt */}
          <section className="mt-6 rounded-md border border-canvas-rule bg-canvas-panel p-6">
            <h3 className="text-sm font-medium text-ink">System prompt</h3>
            <pre className="mt-4 max-h-[420px] overflow-auto whitespace-pre-wrap rounded-sm border border-canvas-rule bg-canvas-inset px-3 py-3 font-mono text-[12px] leading-relaxed text-ink-dim">
              {agent.data.systemPrompt}
            </pre>
          </section>

          {/* Tools — resolved from skills_config.tools[] against the workspace registry */}
          <section className="mt-6 rounded-md border border-canvas-rule bg-canvas-panel p-6">
            <header className="flex items-baseline justify-between">
              <div>
                <h3 className="text-sm font-medium text-ink">Tools</h3>
                <p className="mt-1 text-xs text-ink-dim">
                  Attached via <code className="font-mono text-ink">skills_config.tools[]</code>. Click any tool to open
                  its detail page.
                </p>
              </div>
              <Chip tone="default">{attached.length} attached</Chip>
            </header>

            {tools.isPending && <p className="mt-4 text-sm text-ink-mute">Loading workspace tool registry…</p>}
            {tools.isError && (
              <p className="mt-4 rounded-sm border border-signal-err/40 bg-signal-err/5 px-3 py-2 text-xs text-signal-err">
                Couldn't resolve tools: {tools.error.message}
              </p>
            )}

            {attached.length === 0 && !tools.isPending && (
              <p className="mt-4 rounded-sm border border-dashed border-canvas-rule bg-canvas-inset/60 px-3 py-4 text-center text-xs text-ink-mute">
                No tools attached to this agent.
              </p>
            )}

            {attached.length > 0 && (
              <ul className="mt-4 flex flex-col gap-2">
                {attached.map((a) => (
                  <AttachedToolRow key={a.slug} attached={a} workspaceId={wsId} />
                ))}
              </ul>
            )}
          </section>

          {/* JSONB configs */}
          <section className="mt-6 rounded-md border border-canvas-rule bg-canvas-panel p-6">
            <h3 className="text-sm font-medium text-ink">Runtime configs</h3>
            <p className="mt-1 text-xs text-ink-dim">
              Opaque JSONB blobs — backend doesn't impose a schema on these yet.
            </p>
            <div className="mt-5 grid grid-cols-1 gap-5 md:grid-cols-2">
              <ConfigBlock label="Memory" value={agent.data.memoryConfig} />
              <ConfigBlock label="Schedule" value={agent.data.scheduleConfig} />
              <ConfigBlock label="Guardrails" value={agent.data.guardrailsConfig} />
              <ConfigBlock label="Interaction rules" value={agent.data.interactionRules} />
              <ConfigBlock label="Limits" value={agent.data.limitsConfig} />
              <ConfigBlock label="Skills" value={agent.data.skillsConfig} />
            </div>
          </section>

          {/* Audit */}
          <section className="mt-6 rounded-md border border-canvas-rule bg-canvas-panel p-6">
            <h3 className="text-sm font-medium text-ink">Audit</h3>
            <dl className="mt-4">
              <DetailRow
                label="Created by"
                value={
                  agent.data.createdBy ? (
                    <code className="font-mono text-xs text-ink-dim">{agent.data.createdBy}</code>
                  ) : (
                    <span className="text-ink-mute">— (user deleted)</span>
                  )
                }
              />
              <DetailRow label="Created" value={formatDateTime(agent.data.createdAt)} />
              <DetailRow label="Updated" value={formatDateTime(agent.data.updatedAt)} />
            </dl>
          </section>
        </>
      )}
    </div>
  );
}
