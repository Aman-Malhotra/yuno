import { Link, useParams } from "@tanstack/react-router";
import { ArrowLeft, Pencil, Wrench } from "lucide-react";

import { useTool, useToolVersions, ToolStatusChip, ToolTypeChip, type ToolId } from "@/entities/tool";
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

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[140px_1fr] items-baseline gap-4 border-b border-canvas-rule py-3 last:border-b-0">
      <dt className="eyebrow">{label}</dt>
      <dd className="text-sm text-ink">{value}</dd>
    </div>
  );
}

function JsonBlock({ label, value }: { label: string; value: Record<string, unknown> }) {
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

export function WorkspaceToolDetailPage() {
  const { workspaceId, toolId } = useParams({ from: "/protected/workspaces/$workspaceId/tools/$toolId" });
  const wsId = workspaceId as WorkspaceId;
  const tId = toolId as ToolId;

  const tool = useTool(wsId, tId);
  const versions = useToolVersions(wsId, tId, Boolean(tool.data));

  return (
    <div className="mx-auto w-full max-w-[1180px] px-6 py-8">
      <Link
        to="/workspaces/$workspaceId/tools"
        params={{ workspaceId: wsId }}
        className="mb-4 inline-flex items-center gap-1.5 text-[11px] uppercase tracking-eyebrow text-ink-mute hover:text-ink"
      >
        <ArrowLeft size={12} strokeWidth={1.8} />
        all tools
      </Link>

      {tool.isPending && <p className="text-sm text-ink-mute">Loading tool…</p>}
      {tool.isError && (
        <div className="rounded-md border border-signal-err/40 bg-signal-err/5 p-4 text-sm text-signal-err">
          {tool.error.message}
        </div>
      )}

      {tool.data && (
        <>
          <SectionHeader
            title={
              <span className="inline-flex items-center gap-2">
                <Wrench size={16} strokeWidth={1.6} className="text-ink-mute" />
                <span>{tool.data.name}</span>
              </span>
            }
            meta={
              <span className="flex flex-wrap items-center gap-2 font-mono text-ink-dim">
                <code className="text-xs text-ink-mute">{tool.data.slug}</code>
                <span>·</span>
                <span>v{tool.data.version}</span>
              </span>
            }
            right={
              <div className="flex items-center gap-2">
                <ToolTypeChip type={tool.data.type} />
                <ToolStatusChip status={tool.data.status} />
                {!tool.data.workspaceId && <Chip tone="default">global built-in</Chip>}
                {tool.data.workspaceId && (
                  <Link
                    to="/workspaces/$workspaceId/tools/$toolId/edit"
                    params={{ workspaceId: wsId, toolId: tool.data.id }}
                    className="inline-flex h-7 items-center gap-1.5 rounded-md border border-canvas-ruleStrong bg-canvas-panel px-2.5 text-xs font-medium text-ink transition-colors hover:border-sodium hover:text-sodium"
                  >
                    <Pencil size={12} strokeWidth={1.8} />
                    Edit
                  </Link>
                )}
              </div>
            }
          />

          <div className="hairline-x mt-6" />

          <section className="mt-6 rounded-md border border-canvas-rule bg-canvas-panel p-6">
            <h3 className="text-sm font-medium text-ink">Identity</h3>
            <dl className="mt-4">
              <DetailRow label="Name" value={tool.data.name} />
              <DetailRow
                label="Slug"
                value={<code className="font-mono text-xs text-ink-dim">{tool.data.slug}</code>}
              />
              <DetailRow label="Description" value={tool.data.description} />
              <DetailRow label="Type" value={<ToolTypeChip type={tool.data.type} />} />
              <DetailRow label="Category" value={<span className="font-mono">{tool.data.category}</span>} />
              <DetailRow
                label="Icon"
                value={
                  tool.data.icon ? (
                    <span className="font-mono">{tool.data.icon}</span>
                  ) : (
                    <span className="text-ink-mute">—</span>
                  )
                }
              />
              <DetailRow label="Status" value={<ToolStatusChip status={tool.data.status} />} />
              <DetailRow label="Version" value={<span className="font-mono">v{tool.data.version}</span>} />
              <DetailRow
                label="Tool ID"
                value={<code className="font-mono text-xs text-ink-dim">{tool.data.id}</code>}
              />
            </dl>
          </section>

          <section className="mt-6 rounded-md border border-canvas-rule bg-canvas-panel p-6">
            <h3 className="text-sm font-medium text-ink">Schemas</h3>
            <p className="mt-1 text-xs text-ink-dim">
              JSON Schema for the tool's input and output. The LLM uses input_schema when calling.
            </p>
            <div className="mt-5 grid grid-cols-1 gap-5 md:grid-cols-2">
              <JsonBlock label="Input schema" value={tool.data.inputSchema} />
              <JsonBlock label="Output schema" value={tool.data.outputSchema} />
            </div>
          </section>

          <section className="mt-6 rounded-md border border-canvas-rule bg-canvas-panel p-6">
            <h3 className="text-sm font-medium text-ink">Runtime configuration</h3>
            <p className="mt-1 text-xs text-ink-dim">
              Per-type executor config, auth, guardrails, execution-policy and channel routing.
            </p>
            <div className="mt-5 grid grid-cols-1 gap-5 md:grid-cols-2">
              <JsonBlock label="Config" value={tool.data.config} />
              <JsonBlock label="Auth" value={tool.data.auth} />
              <JsonBlock label="Guardrails" value={tool.data.guardrails} />
              <JsonBlock label="Execution policy" value={tool.data.executionPolicy} />
              <JsonBlock label="Channels" value={tool.data.channels} />
            </div>
          </section>

          <section className="mt-6 rounded-md border border-canvas-rule bg-canvas-panel p-6">
            <header className="flex items-baseline justify-between">
              <div>
                <h3 className="text-sm font-medium text-ink">Versions</h3>
                <p className="mt-1 text-xs text-ink-dim">Each save creates a new immutable snapshot.</p>
              </div>
              {versions.data && <Chip tone="default">{versions.data.length} total</Chip>}
            </header>
            {versions.isPending && <p className="mt-4 text-sm text-ink-mute">Loading versions…</p>}
            {versions.isError && (
              <p className="mt-4 text-xs text-signal-err">{versions.error?.message ?? "Couldn't load versions."}</p>
            )}
            {versions.data && versions.data.length > 0 && (
              <ul className="mt-4 flex flex-col divide-y divide-canvas-rule">
                {versions.data.map((v) => (
                  <li key={v.id} className="flex items-center justify-between gap-3 py-2 text-xs">
                    <span className="font-mono text-ink">v{v.versionNumber}</span>
                    <span className="truncate text-ink-dim">{v.name}</span>
                    <span className="font-mono text-ink-mute">{formatDateTime(v.createdAt)}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="mt-6 rounded-md border border-canvas-rule bg-canvas-panel p-6">
            <h3 className="text-sm font-medium text-ink">Audit</h3>
            <dl className="mt-4">
              <DetailRow
                label="Created by"
                value={
                  tool.data.createdBy ? (
                    <code className="font-mono text-xs text-ink-dim">{tool.data.createdBy}</code>
                  ) : (
                    <span className="text-ink-mute">— (user deleted)</span>
                  )
                }
              />
              <DetailRow label="Created" value={formatDateTime(tool.data.createdAt)} />
              <DetailRow label="Updated" value={formatDateTime(tool.data.updatedAt)} />
            </dl>
          </section>

          <section className="mt-6 rounded-md border border-canvas-rule bg-canvas-panel p-6">
            <h3 className="text-sm font-medium text-ink">Using this tool</h3>
            <p className="mt-2 text-xs text-ink-dim">
              Attach to an agent by appending an entry to its{" "}
              <code className="font-mono text-ink">skills_config.tools</code> array:
            </p>
            <pre className="mt-3 overflow-x-auto rounded-sm border border-canvas-rule bg-canvas-inset px-3 py-3 font-mono text-[11px] leading-relaxed text-ink-dim">
              {JSON.stringify({ name: tool.data.slug, options: {} }, null, 2)}
            </pre>
          </section>
        </>
      )}
    </div>
  );
}
