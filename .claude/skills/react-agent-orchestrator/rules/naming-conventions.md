---
title: Naming Conventions
impact: LOW
impactDescription: Consistent names mean grep finds it the first try; inconsistency costs minutes per lookup, daily
tags: naming, conventions
---

## Naming Conventions

| Kind                     | Convention                       | Example                                |
|--------------------------|----------------------------------|----------------------------------------|
| React component          | PascalCase                       | `AgentCard.tsx`, `WorkflowCanvas.tsx`  |
| Hook                     | `useSomething`                   | `useAgent`, `useWorkflowBuilderStore`  |
| Zustand store hook       | `useSomethingStore`              | `useWorkflowBuilderStore`              |
| Zod schema               | `somethingSchema`                | `agentSchema`, `createAgentSchema`     |
| Inferred type from schema| Same as the domain noun          | `type Agent = z.infer<typeof agentSchema>` |
| API client object        | `somethingApi`                   | `agentApi.list`, `workflowApi.create`  |
| Query key factory        | `somethingQueryKeys`             | `agentQueryKeys.detail(id)`            |
| Read query hook          | `useSomething(...)` / `useSomethings(...)` | `useAgent`, `useAgents`      |
| Mutation hook            | `useVerbSomething`               | `useCreateAgent`, `useDeleteWorkflow`  |
| Pure function            | verbNoun, camelCase              | `validateWorkflow`, `serializeWorkflow`|
| Branded id               | PascalCase noun + `Id`           | `AgentId`, `WorkflowId`, `RunId`       |
| Constants                | `SCREAMING_SNAKE_CASE`           | `MAX_NODES_PER_WORKFLOW`               |
| Folder                   | kebab-case                       | `agent-editor/`, `configure-llm/`      |
| Index export             | `index.ts`                       | one per module / entity / feature      |

### Files

- Schema: `*.schema.ts`
- Types: `*.types.ts`
- API client: `*.api.ts`
- Query hooks: `*.queries.ts`
- Mutation hooks: `*.mutations.ts`
- Store: `*.store.ts`
- Pure helpers: descriptive verb-noun, e.g. `validate-workflow.ts`

### Avoid

- Suffixes like `Util`, `Helper`, `Manager`, `Service` on the frontend — they always end up as catch-alls
- Plural folder names like `components/`, `hooks/` at the top level — those are the layer-first folders we explicitly reject ([[arch-feature-modules]])
- Abbreviations: `agnt`, `wf`, `prov` — spell it out, autocomplete is free

### Examples

```txt
entities/agent/
  model/
    agent.types.ts
    agent.schema.ts
  api/
    agent.api.ts
    agent.queries.ts
    agent.mutations.ts
  ui/
    AgentCard.tsx
    AgentStatusBadge.tsx
  index.ts
```

```ts
// hook + store + schema + api in one mental model
const agents = useAgents({ status: "active" });
const createAgent = useCreateAgent();
const selectedAgentId = useAgentsViewStore((s) => s.selectedAgentId);
const parsed = agentSchema.parse(rawJson);
const detail = await agentApi.getById(agentId);
```

See: [[arch-feature-modules]], [[ts-strict]]
