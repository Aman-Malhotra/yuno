---
title: Central Query Key Factories
impact: MEDIUM
impactDescription: Hand-typed `["agents", id]` keys drift; mutations then fail to invalidate the right queries
tags: api, tanstack-query, cache-keys
---

## Central Query Key Factories

One key factory per entity. All `useQuery` / `useMutation` invalidations go through it.

### Factory

```ts
// entities/agent/api/agent.queries.ts
import { queryOptions } from "@tanstack/react-query";

export const agentQueryKeys = {
  all: ["agents"] as const,
  lists: () => [...agentQueryKeys.all, "list"] as const,
  list: (filters: AgentFilters) => [...agentQueryKeys.lists(), filters] as const,
  details: () => [...agentQueryKeys.all, "detail"] as const,
  detail: (id: AgentId) => [...agentQueryKeys.details(), id] as const,
  versions: (id: AgentId) => [...agentQueryKeys.detail(id), "versions"] as const,
} as const;
```

### Hooks

```ts
export function useAgent(id: AgentId) {
  return useQuery({
    queryKey: agentQueryKeys.detail(id),
    queryFn: () => agentApi.getById(id),
  });
}

export function useAgents(filters: AgentFilters = {}) {
  return useQuery({
    queryKey: agentQueryKeys.list(filters),
    queryFn: () => agentApi.list(filters),
  });
}
```

### Mutations invalidate by prefix

```ts
export function useUpdateAgent(id: AgentId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: Partial<CreateAgentInput>) => agentApi.update(id, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: agentQueryKeys.detail(id) });
      qc.invalidateQueries({ queryKey: agentQueryKeys.lists() });
    },
  });
}
```

### Yuno entity keys

| Entity        | Factory file                                   |
|---------------|------------------------------------------------|
| agent         | `entities/agent/api/agent.queries.ts`          |
| workflow      | `entities/workflow/api/workflow.queries.ts`    |
| llm-provider  | `entities/llm-provider/api/llm-provider.queries.ts` |
| tool          | `entities/tool/api/tool.queries.ts`            |
| channel       | `entities/channel/api/channel.queries.ts`      |
| run           | `entities/run/api/run.queries.ts`              |

### Bad

```ts
// ❌ duplicated string keys, can't invalidate "all agent details"
useQuery({ queryKey: ["agent", id], queryFn: ... });
useQuery({ queryKey: ["agents", id], queryFn: ... }); // typo, separate cache
qc.invalidateQueries({ queryKey: ["agent", id] });    // doesn't hit the lists
```

### Good

```ts
useQuery({ queryKey: agentQueryKeys.detail(id), queryFn: ... });
qc.invalidateQueries({ queryKey: agentQueryKeys.all }); // nukes lists + details
```

See: [[state-server-tanstack-query]], [[api-http-client]]
