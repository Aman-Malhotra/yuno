---
title: Module Boundaries via index.ts
impact: CRITICAL
impactDescription: Internal imports lock the workflow builder's internals into other modules — refactors break everything
tags: architecture, encapsulation, public-api
---

## Module Boundaries via `index.ts`

Each module and entity exposes a **public API** through a single `index.ts`. Other modules import from that file only.

### Standard module layout

```txt
modules/workflow-builder/
  ui/                          # React components
  nodes/                       # node component implementations
  edges/                       # edge component implementations
  model/                       # local types, stores, schemas
  lib/                         # pure functions (validation, layout)
  config/                      # constants, registries
  index.ts                     # ← the only public surface
```

### Good `index.ts`

```ts
// modules/workflow-builder/index.ts
export { WorkflowBuilderPage } from "./ui/WorkflowBuilderPage";
export { useWorkflowBuilderStore } from "./model/workflow-builder.store";
export type { WorkflowBuilderState } from "./model/workflow-builder.store";
```

### Good external import

```ts
import { WorkflowBuilderPage } from "@/modules/workflow-builder";
```

### Forbidden — reaching into internals

```ts
import { WorkflowBuilderPage } from "@/modules/workflow-builder/ui/WorkflowBuilderPage"; // ❌
import { validateWorkflow }    from "@/modules/workflow-builder/lib/validate";           // ❌
```

If another module needs a piece, either:

1. Export it from `index.ts` deliberately, or
2. Move the piece down to `entities/` or `shared/`

### Enforce with ESLint

```js
// .eslintrc.cjs
{
  rules: {
    "no-restricted-imports": ["error", {
      patterns: [
        "@/modules/*/ui/**",
        "@/modules/*/nodes/**",
        "@/modules/*/edges/**",
        "@/modules/*/model/**",
        "@/modules/*/lib/**",
        "@/modules/*/config/**",
        "@/entities/*/api/**",
        "@/entities/*/model/**",
        "@/entities/*/ui/**"
      ]
    }]
  }
}
```

### Same rule applies to entities

```ts
// entities/agent/index.ts
export { AgentCard } from "./ui/AgentCard";
export { AgentStatusBadge } from "./ui/AgentStatusBadge";
export { agentSchema } from "./model/agent.schema";
export type { Agent, AgentId } from "./model/agent.types";
export { useAgent, useAgents } from "./api/agent.queries";
export { useCreateAgent, useUpdateAgent, useDeleteAgent } from "./api/agent.mutations";
```

See: [[arch-feature-modules]], [[arch-dependency-direction]]
