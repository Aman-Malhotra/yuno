---
title: Strict TypeScript + Branded IDs
impact: MEDIUM
impactDescription: Passing an `AgentId` where a `WorkflowId` is expected is a one-character bug; branded ids make it impossible at compile time
tags: typescript, strict-mode, branded-types
---

## Strict TypeScript + Branded IDs

### `tsconfig.json` baseline

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "exactOptionalPropertyTypes": true,
    "noFallthroughCasesInSwitch": true,
    "isolatedModules": true,
    "skipLibCheck": true,
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] }
  }
}
```

### Type vs interface

- `type` for object shapes
- `interface` only when you need declaration merging or extensible public contracts (rare)
- Zod schemas for any value that crosses the API or form boundary

### Never `any`

Prefer `unknown` + parsing. Reach for `as` only at framework seams (React Flow's `NodeProps<unknown>`) and immediately narrow.

### Branded IDs

The product traffics in a lot of stringly-typed identifiers. Brand them.

```ts
// shared/types/brand.ts
export type Brand<T, Name extends string> = T & { readonly __brand: Name };

// entities/agent/model/agent.types.ts
export type AgentId    = Brand<string, "AgentId">;

// entities/workflow/model/workflow.types.ts
export type WorkflowId = Brand<string, "WorkflowId">;
export type NodeId     = Brand<string, "NodeId">;
export type EdgeId     = Brand<string, "EdgeId">;

// entities/run/model/run.types.ts
export type RunId      = Brand<string, "RunId">;

// entities/llm-provider/model/llm-provider.types.ts
export type ProviderId = Brand<string, "ProviderId">;

// entities/tool/model/tool.types.ts
export type ToolId     = Brand<string, "ToolId">;

// entities/channel/model/channel.types.ts
export type ChannelId  = Brand<string, "ChannelId">;
```

### Creating branded ids

Only at the boundary — inside Zod schemas:

```ts
// entities/agent/model/agent.schema.ts
import { z } from "zod";
import type { AgentId } from "./agent.types";

const agentIdSchema = z.string().min(1).transform((s) => s as AgentId);

export const agentSchema = z.object({
  id: agentIdSchema,
  name: z.string(),
  // ...
});
```

### Caught at compile time

```ts
function loadAgent(id: AgentId) { /* ... */ }
function loadWorkflow(id: WorkflowId) { /* ... */ }

const wfId: WorkflowId = /* ... */;
loadAgent(wfId); // ❌ TS error — exactly what we want
```

See: [[api-http-client]], [[naming-conventions]]
