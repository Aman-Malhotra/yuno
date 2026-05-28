---
title: Forms = React Hook Form + Zod
impact: CRITICAL
impactDescription: Hand-rolled form state in agent/workflow forms re-renders on every keystroke and skips validation parity with the backend
tags: state, forms, react-hook-form, zod, validation
---

## Forms = React Hook Form + Zod

Every form in the app uses React Hook Form with `zodResolver`. The Zod schema is the single source of truth — shared with the backend API contract where possible.

### Schema co-located with the form

```ts
// features/create-agent/model/create-agent.form.ts
import { z } from "zod";

export const createAgentSchema = z.object({
  name: z.string().min(1, "Name is required").max(80),
  role: z.string().min(1),
  description: z.string().max(500).optional(),
  providerId: z.string().min(1),
  model: z.string().min(1),
  systemPrompt: z.string().min(1, "System prompt is required"),
  temperature: z.number().min(0).max(2).default(0.7),
  maxTokens: z.number().int().positive().optional(),
  toolIds: z.array(z.string()).default([]),
  channelIds: z.array(z.string()).default([]),
  memory: z.object({
    enabled: z.boolean(),
    type: z.enum(["none", "buffer", "vector"]).default("none"),
    retentionDays: z.number().int().positive().optional(),
  }).default({ enabled: false, type: "none" }),
  guardrails: z.object({
    maxStepsPerRun: z.number().int().positive().default(20),
    maxCostUsd: z.number().positive().optional(),
  }).default({ maxStepsPerRun: 20 }),
});

export type CreateAgentInput = z.infer<typeof createAgentSchema>;
```

### Form component pattern

```tsx
// features/create-agent/ui/CreateAgentForm.tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

export function CreateAgentForm({ onSuccess }: { onSuccess: (id: AgentId) => void }) {
  const form = useForm<CreateAgentInput>({
    resolver: zodResolver(createAgentSchema),
    defaultValues: {
      temperature: 0.7,
      toolIds: [],
      channelIds: [],
      memory: { enabled: false, type: "none" },
      guardrails: { maxStepsPerRun: 20 },
    },
  });

  const createAgent = useCreateAgent();

  const onSubmit = form.handleSubmit(async (input) => {
    const agent = await createAgent.mutateAsync(input);
    onSuccess(agent.id);
  });

  return <form onSubmit={onSubmit}>{/* ... */}</form>;
}
```

### Multi-step forms (agent creation stepper)

Keep one schema per step, then a final `mergedSchema` for the submit payload. Use `form.trigger(["name", "role"])` to validate the current step before advancing.

See: [[agent-creation-stepper]] for the full stepper layout.

### Bad — Zustand-as-form-state

```ts
// ❌ No validation, no field-level errors, manual `dirty` tracking
const useCreateAgentDraft = create((set) => ({
  name: "",
  setName: (name) => set({ name }),
  // ... 30 more setters
}));
```

### Rule

If it has `<input>`, `<select>`, or `<textarea>` and gets submitted, it's React Hook Form + Zod.

See: [[state-server-tanstack-query]], [[agent-creation-stepper]]
