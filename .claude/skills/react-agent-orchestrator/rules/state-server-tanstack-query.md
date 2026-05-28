---
title: Server State Lives in TanStack Query
impact: CRITICAL
impactDescription: Mirroring server data into Zustand creates two sources of truth that drift during live runs
tags: state, tanstack-query, caching
---

## Server State Lives in TanStack Query

Anything that came from the backend belongs in TanStack Query. **Never** mirror it into Zustand "for convenience".

### What counts as server state in Yuno

- agents list, agent detail
- workflows list, workflow detail (canvas data)
- LLM provider configs and model lists
- tool registry
- channel configs (WhatsApp/Telegram/Slack)
- runs list, run detail, run events, inter-agent messages
- user/project/billing

### Query hook standard

```ts
// entities/agent/api/agent.queries.ts
export function useAgent(agentId: AgentId) {
  return useQuery({
    queryKey: agentQueryKeys.detail(agentId),
    queryFn: () => agentApi.getById(agentId),
  });
}

export function useAgents(filters: AgentFilters) {
  return useQuery({
    queryKey: agentQueryKeys.list(filters),
    queryFn: () => agentApi.list(filters),
  });
}
```

### Mutation hook standard

```ts
// entities/agent/api/agent.mutations.ts
export function useCreateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: agentApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: agentQueryKeys.lists() });
    },
  });
}
```

### Bad — duplicating server data in Zustand

```ts
// ❌ Will desync on the first websocket update
type AgentsStore = {
  agents: Agent[];
  setAgents: (a: Agent[]) => void;
};
```

### Good — derived view state only

```ts
// ✅ Zustand stores selection, query owns the list
type AgentsViewStore = {
  selectedAgentId: AgentId | null;
  setSelectedAgentId: (id: AgentId | null) => void;
};
```

### Realtime updates feed back into Query

When an SSE/WS run event arrives, update the cache directly — don't reach into Zustand:

```ts
queryClient.setQueryData(
  runQueryKeys.events(runId),
  (prev: RunEvent[] = []) => [...prev, event],
);
```

See: [[state-local-zustand]], [[api-query-keys]], [[realtime-run-events]]
