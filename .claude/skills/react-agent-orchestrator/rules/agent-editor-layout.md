---
title: Agent Editor Layout
impact: HIGH
impactDescription: Yuno's evaluation rewards configurability and live-test ergonomics — a three-column editor delivers both
tags: agent, editor, layout, ux
---

## Agent Editor Layout

The editor is the screen users live in once an agent exists. Three columns:

```
┌──────────────┬─────────────────────────┬────────────────┐
│  Sections    │       Editor            │  Test Console  │
│              │                         │                │
│ • Overview   │  (selected section's    │  Chat-style    │
│ • Prompt     │   form / editor)        │  test panel,   │
│ • LLM        │                         │  streams from  │
│ • Tools      │                         │  real runtime  │
│ • Memory     │                         │                │
│ • Channels   │                         │  Token / cost  │
│ • Guardrails │                         │  meter         │
│ • Versions   │                         │                │
└──────────────┴─────────────────────────┴────────────────┘
```

### Why three columns

- **Left** answers "what can I configure?" — discoverability
- **Center** is the focused editor — Monaco for prompts, schema forms for everything else
- **Right** is the live test console — closes the feedback loop the Yuno demo will be judged on

### Folder layout

```txt
modules/agent-editor/
  ui/
    AgentEditorPage.tsx
    AgentEditorLayout.tsx          # three-column shell
    AgentSectionsNav.tsx           # left
    AgentOverviewPanel.tsx
    AgentPromptEditor.tsx          # Monaco
    AgentLlmConfigPanel.tsx        # uses features/configure-llm
    AgentToolsPanel.tsx            # uses features/configure-tool
    AgentMemoryPanel.tsx           # uses features/manage-memory
    AgentChannelsPanel.tsx         # uses features/connect-channel
    AgentGuardrailsPanel.tsx
    AgentVersionHistory.tsx
    AgentTestConsole.tsx           # right — uses features/test-agent
  model/
    agent-editor.store.ts          # selected section, dirty flags
  index.ts
```

### Save semantics

- Every panel autosaves on blur via a per-section mutation (`useUpdateAgent`)
- Toolbar shows a `Saved · 12s ago` indicator backed by the mutation status
- The test console always uses the **latest saved** version — surface a warning if there are unsaved edits

### Test console must use the real runtime

This is the Yuno demo screen. It must hit the backend runtime (LangGraph/CrewAI/AutoGen/etc.), not a frontend mock:

```ts
// features/test-agent/api/useTestAgent.ts
export function useTestAgent(agentId: AgentId) {
  return useMutation({
    mutationFn: ({ message }: { message: string }) =>
      agentApi.startTestRun(agentId, message),
  });
}
```

Streaming events come back via the realtime channel — see [[realtime-run-events]].

### Version history is a query, not local state

```ts
export function useAgentVersions(agentId: AgentId) {
  return useQuery({
    queryKey: agentQueryKeys.versions(agentId),
    queryFn: () => agentApi.listVersions(agentId),
  });
}
```

See: [[agent-creation-stepper]], [[agent-feature-reuse]], [[realtime-run-events]]
