import { useMemo } from "react";
import { Link } from "@tanstack/react-router";
import { ExternalLink } from "lucide-react";

import { useAgent, useAgentsInWorkspace, type AgentId, type AgentSummary } from "@/entities/agent";
import { useTool, useToolsInWorkspace, type ToolId, type ToolSummary } from "@/entities/tool";
import type {
  EdgeId,
  NodeId,
  WorkflowEdgeCondition,
  WorkflowEdgeConditionKind,
  WorkflowNodeData,
} from "@/entities/workflow";
import type { WorkspaceId } from "@/entities/workspace";
import { Chip, Field, Input, Select } from "@/shared/ui";

import { useWorkflowBuilderStore } from "../model/workflow-builder.store";

type Props = { workspaceId: WorkspaceId };

export function WorkflowInspector({ workspaceId }: Props) {
  const selectedNodeId = useWorkflowBuilderStore((s) => s.selectedNodeId);
  const selectedEdgeId = useWorkflowBuilderStore((s) => s.selectedEdgeId);
  const nodes = useWorkflowBuilderStore((s) => s.nodes);
  const edges = useWorkflowBuilderStore((s) => s.edges);

  const selectedNode = useMemo(() => nodes.find((n) => n.id === selectedNodeId) ?? null, [nodes, selectedNodeId]);
  const selectedEdge = useMemo(() => edges.find((e) => e.id === selectedEdgeId) ?? null, [edges, selectedEdgeId]);

  return (
    <aside className="w-80 shrink-0 overflow-y-auto border-l border-canvas-rule bg-canvas-panel p-4">
      <h2 className="mb-3 text-[10px] font-semibold uppercase tracking-eyebrow text-ink-mute">Inspector</h2>

      {!selectedNode && !selectedEdge && <p className="text-xs text-ink-dim">Select a node or edge to configure it.</p>}

      {selectedNode && (
        <NodeInspector workspaceId={workspaceId} nodeId={selectedNode.id as NodeId} data={selectedNode.data} />
      )}

      {selectedEdge && !selectedNode && (
        <EdgeInspector edgeId={selectedEdge.id as EdgeId} condition={selectedEdge.data?.condition} />
      )}
    </aside>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Node inspector
// ──────────────────────────────────────────────────────────────────────

function NodeInspector({
  workspaceId,
  nodeId,
  data,
}: {
  workspaceId: WorkspaceId;
  nodeId: NodeId;
  data: WorkflowNodeData;
}) {
  const updateNodeData = useWorkflowBuilderStore((s) => s.updateNodeData);
  const removeNode = useWorkflowBuilderStore((s) => s.removeNode);

  return (
    <div className="flex flex-col gap-3">
      <div className="text-[10px] uppercase tracking-eyebrow text-ink-faint">{data.type}</div>

      <Field label="Label">
        <Input
          value={data.label}
          onChange={(e) => updateNodeData(nodeId, { label: e.target.value })}
          placeholder="Display name"
        />
      </Field>

      {data.type === "agent" && (
        <AgentNodeFields
          workspaceId={workspaceId}
          agentId={(data.config["agentId"] as string | null) ?? null}
          inputTemplate={(data.config["input"] as string | undefined) ?? ""}
          onAgentIdChange={(agentId) =>
            updateNodeData(nodeId, (d) => ({ ...d, config: { ...d.config, agentId } }))
          }
          onInputChange={(input) => updateNodeData(nodeId, (d) => ({ ...d, config: { ...d.config, input } }))}
        />
      )}

      {data.type === "tool" && (
        <ToolNodeFields
          workspaceId={workspaceId}
          toolId={(data.config["toolId"] as string | null) ?? null}
          onToolIdChange={(toolId) => updateNodeData(nodeId, (d) => ({ ...d, config: { ...d.config, toolId } }))}
        />
      )}

      {data.type === "condition" && (
        <Field label="Expression" hint="Safe DSL evaluated against run state.">
          <Input
            value={(data.config["expression"] as string | undefined) ?? ""}
            onChange={(e) =>
              updateNodeData(nodeId, (d) => ({
                ...d,
                config: { ...d.config, expression: e.target.value },
              }))
            }
            placeholder="state.intent == 'billing'"
          />
        </Field>
      )}

      {data.type !== "start" && (
        <button
          type="button"
          onClick={() => removeNode(nodeId)}
          className="mt-2 self-start text-[11px] uppercase tracking-eyebrow text-signal-err hover:underline"
        >
          Delete node
        </button>
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Agent node — picker + live detail card + deep link
// ──────────────────────────────────────────────────────────────────────

function AgentNodeFields({
  workspaceId,
  agentId,
  inputTemplate,
  onAgentIdChange,
  onInputChange,
}: {
  workspaceId: WorkspaceId;
  agentId: string | null;
  inputTemplate: string;
  onAgentIdChange: (id: string | null) => void;
  onInputChange: (v: string) => void;
}) {
  const agents = useAgentsInWorkspace(workspaceId);

  const options = useMemo(() => {
    const items = agents.data?.items ?? [];
    return [
      { value: "", label: "— select agent —" },
      ...items.map((a: AgentSummary) => ({ value: a.id, label: a.name })),
    ];
  }, [agents.data?.items]);

  return (
    <>
      <Field label="Agent">
        <Select
          value={agentId ?? ""}
          options={options}
          onChange={(e) => onAgentIdChange(e.target.value ? e.target.value : null)}
        />
      </Field>

      {agentId && <AgentDetailCard workspaceId={workspaceId} agentId={agentId as AgentId} />}

      <Field label="Input template" hint="Mustache-style placeholders, e.g. {{message.text}}">
        <Input
          value={inputTemplate}
          onChange={(e) => onInputChange(e.target.value)}
          placeholder="{{message.text}}"
        />
      </Field>
    </>
  );
}

function AgentDetailCard({ workspaceId, agentId }: { workspaceId: WorkspaceId; agentId: AgentId }) {
  const { data: agent, isPending, error } = useAgent(workspaceId, agentId);

  if (isPending) {
    return <div className="h-16 animate-pulse rounded-md border border-canvas-rule bg-canvas/40" />;
  }
  if (error || !agent) {
    return (
      <div className="rounded-md border border-signal-err/40 bg-signal-err/5 p-2.5 text-[11px] text-signal-err">
        {error?.message ?? "Agent not found in this workspace."}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 rounded-md border border-canvas-rule bg-canvas/40 p-2.5">
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-xs font-medium text-ink">{agent.name}</div>
          <div className="truncate font-mono text-[10px] text-ink-mute">{agent.slug}</div>
        </div>
        <Chip tone={agent.status === "active" ? "ok" : "warn"}>{agent.status}</Chip>
      </div>

      <DetailRow label="Role" value={agent.role} />
      <DetailRow label="Model" value={`${agent.modelProvider} · ${agent.modelName}`} mono />
      {agent.description && (
        <p className="line-clamp-3 text-[11px] leading-relaxed text-ink-dim">{agent.description}</p>
      )}

      <Link
        to="/workspaces/$workspaceId/agents/$agentId"
        params={{ workspaceId, agentId }}
        className="mt-1 inline-flex items-center gap-1 self-start text-[11px] font-medium uppercase tracking-eyebrow text-sodium hover:underline"
      >
        Open agent
        <ExternalLink size={11} strokeWidth={1.8} />
      </Link>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Tool node — picker + live detail card + deep link
// ──────────────────────────────────────────────────────────────────────

function ToolNodeFields({
  workspaceId,
  toolId,
  onToolIdChange,
}: {
  workspaceId: WorkspaceId;
  toolId: string | null;
  onToolIdChange: (id: string | null) => void;
}) {
  const tools = useToolsInWorkspace(workspaceId);

  const options = useMemo(() => {
    const items = tools.data?.items ?? [];
    return [
      { value: "", label: "— select tool —" },
      ...items.map((t: ToolSummary) => ({ value: t.id, label: t.name })),
    ];
  }, [tools.data?.items]);

  return (
    <>
      <Field label="Tool">
        <Select
          value={toolId ?? ""}
          options={options}
          onChange={(e) => onToolIdChange(e.target.value ? e.target.value : null)}
        />
      </Field>

      {toolId && <ToolDetailCard workspaceId={workspaceId} toolId={toolId as ToolId} />}
    </>
  );
}

function ToolDetailCard({ workspaceId, toolId }: { workspaceId: WorkspaceId; toolId: ToolId }) {
  const { data: tool, isPending, error } = useTool(workspaceId, toolId);

  if (isPending) {
    return <div className="h-16 animate-pulse rounded-md border border-canvas-rule bg-canvas/40" />;
  }
  if (error || !tool) {
    return (
      <div className="rounded-md border border-signal-err/40 bg-signal-err/5 p-2.5 text-[11px] text-signal-err">
        {error?.message ?? "Tool not found in this workspace."}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 rounded-md border border-canvas-rule bg-canvas/40 p-2.5">
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-xs font-medium text-ink">{tool.name}</div>
          <div className="truncate font-mono text-[10px] text-ink-mute">{tool.slug}</div>
        </div>
        <Chip tone={tool.status === "active" ? "ok" : "warn"}>{tool.status}</Chip>
      </div>

      <DetailRow label="Type" value={tool.type} mono />
      <DetailRow label="Category" value={tool.category} />
      <DetailRow label="Version" value={`v${tool.version}`} mono />
      {tool.description && (
        <p className="line-clamp-3 text-[11px] leading-relaxed text-ink-dim">{tool.description}</p>
      )}

      <Link
        to="/workspaces/$workspaceId/tools/$toolId"
        params={{ workspaceId, toolId }}
        className="mt-1 inline-flex items-center gap-1 self-start text-[11px] font-medium uppercase tracking-eyebrow text-sodium hover:underline"
      >
        Open tool
        <ExternalLink size={11} strokeWidth={1.8} />
      </Link>
    </div>
  );
}

function DetailRow({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline gap-2 text-[11px]">
      <span className="w-16 shrink-0 text-ink-mute">{label}</span>
      <span className={mono ? "truncate font-mono text-ink-dim" : "truncate text-ink-dim"}>{value}</span>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────
// Edge inspector — condition editor
// ──────────────────────────────────────────────────────────────────────

const CONDITION_OPTIONS: { value: WorkflowEdgeConditionKind; label: string }[] = [
  { value: "always", label: "Always" },
  { value: "equals", label: "Equals (state[path] === value)" },
  { value: "expr", label: "Expression (DSL)" },
];

function EdgeInspector({ edgeId, condition }: { edgeId: EdgeId; condition: WorkflowEdgeCondition | undefined }) {
  const updateEdgeCondition = useWorkflowBuilderStore((s) => s.updateEdgeCondition);
  const removeEdge = useWorkflowBuilderStore((s) => s.removeEdge);
  const kind: WorkflowEdgeConditionKind = condition?.kind ?? "always";

  return (
    <div className="flex flex-col gap-3">
      <div className="text-[10px] uppercase tracking-eyebrow text-ink-faint">edge</div>

      <Field label="Routing">
        <Select
          value={kind}
          options={CONDITION_OPTIONS}
          onChange={(e) =>
            updateEdgeCondition(edgeId, {
              kind: e.target.value as WorkflowEdgeConditionKind,
              path: condition?.path,
              value: condition?.value,
              expr: condition?.expr,
            })
          }
        />
      </Field>

      {kind === "equals" && (
        <>
          <Field label="Path" hint="Dotted path on run state, e.g. `intent`.">
            <Input
              value={condition?.path ?? ""}
              onChange={(e) => updateEdgeCondition(edgeId, { ...condition!, kind: "equals", path: e.target.value })}
              placeholder="intent"
            />
          </Field>
          <Field label="Value">
            <Input
              value={String(condition?.value ?? "")}
              onChange={(e) => updateEdgeCondition(edgeId, { ...condition!, kind: "equals", value: e.target.value })}
              placeholder="billing"
            />
          </Field>
        </>
      )}

      {kind === "expr" && (
        <Field label="Expression" hint="Safe DSL evaluated on run state.">
          <Input
            value={condition?.expr ?? ""}
            onChange={(e) => updateEdgeCondition(edgeId, { ...condition!, kind: "expr", expr: e.target.value })}
            placeholder="state.score > 0.7"
          />
        </Field>
      )}

      <button
        type="button"
        onClick={() => removeEdge(edgeId)}
        className="mt-2 self-start text-[11px] uppercase tracking-eyebrow text-signal-err hover:underline"
      >
        Delete edge
      </button>
    </div>
  );
}
