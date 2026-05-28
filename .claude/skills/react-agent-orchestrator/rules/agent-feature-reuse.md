---
title: Reuse Configuration Features Across Create and Edit
impact: HIGH
impactDescription: Duplicating LLM/tool/memory forms between create-agent and edit-agent doubles the maintenance surface and guarantees they drift
tags: agent, features, reuse, dry
---

## Reuse Configuration Features Across Create and Edit

The agent creation stepper and the agent editor both configure the same things. Extract each concern as a `features/*` folder and mount it from both modules.

### Features

| Feature                   | Used by                                      | Inputs                       |
|---------------------------|----------------------------------------------|------------------------------|
| `features/configure-llm`  | `agent-creation/AgentLlmStep`, `agent-editor/AgentLlmConfigPanel` | provider, model, temp, maxTokens, responseFormat |
| `features/configure-tool` | `agent-creation/AgentToolsStep`, `agent-editor/AgentToolsPanel`   | toolIds, per-tool config     |
| `features/manage-memory`  | `agent-creation/AgentMemoryStep`, `agent-editor/AgentMemoryPanel` | type, vectorStoreId, retention |
| `features/connect-channel`| `agent-creation/AgentChannelsStep`, `agent-editor/AgentChannelsPanel` | channelIds + per-channel config |
| `features/test-agent`     | `agent-editor/AgentTestConsole`              | message → run                |

### Feature shape

```txt
features/configure-llm/
  ui/
    LlmConfigForm.tsx            # the actual form fields
    ProviderModelSelect.tsx
  model/
    llm-config.schema.ts         # exported Zod schema
  index.ts
```

### The feature exports a controlled form fragment

Forms in steps and panels share the same parent `useForm` context. The feature exposes field components that read from the parent form via `useFormContext`:

```tsx
// features/configure-llm/ui/LlmConfigForm.tsx
import { useFormContext } from "react-hook-form";
import type { CreateAgentInput } from "@/features/create-agent";

export function LlmConfigForm() {
  const form = useFormContext<Pick<CreateAgentInput, "providerId" | "model" | "temperature" | "maxTokens">>();
  // render fields bound to form.register / Controller
}
```

This works whether the parent is the create-agent form or the edit-agent form — both expose the same field paths.

### Schemas are shared, not redeclared

```ts
// features/configure-llm/model/llm-config.schema.ts
export const llmConfigSchema = z.object({
  providerId: z.string().min(1),
  model: z.string().min(1),
  temperature: z.number().min(0).max(2).default(0.7),
  maxTokens: z.number().int().positive().optional(),
  responseFormat: z.enum(["text", "json"]).default("text"),
});

// features/create-agent/model/create-agent.form.ts
import { llmConfigSchema } from "@/features/configure-llm";

export const createAgentSchema = z.object({
  name: z.string().min(1),
  // ...
}).and(llmConfigSchema);
```

### Anti-pattern

```ts
// ❌ Two copies of the same form, two schemas, guaranteed drift
modules/agent-creation/ui/AgentLlmStep.tsx        // 200 lines of fields
modules/agent-editor/ui/AgentLlmConfigPanel.tsx   // 200 lines of fields again
```

See: [[agent-creation-stepper]], [[agent-editor-layout]], [[state-form-rhf-zod]]
