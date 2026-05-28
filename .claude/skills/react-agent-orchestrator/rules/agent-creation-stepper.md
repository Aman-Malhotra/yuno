---
title: Agent Creation Stepper
impact: HIGH
impactDescription: Agent config has 6 distinct concerns — a single mega-form drowns the user; a stepper makes it teachable
tags: agent, forms, stepper, ux
---

## Agent Creation Stepper

A single agent has six configuration concerns from the Yuno spec: identity, LLM, prompt, tools, memory, channels/guardrails. Build it as a stepper, not a 40-field form.

### Steps

| # | Step           | Fields                                                                 |
|---|----------------|------------------------------------------------------------------------|
| 1 | Basics         | name, role, description, tags                                          |
| 2 | LLM            | providerId, model, temperature, maxTokens, responseFormat              |
| 3 | Prompt         | systemPrompt (Monaco editor), prompt variables                         |
| 4 | Tools          | available tools (registry), selected toolIds, per-tool config          |
| 5 | Memory         | enabled, type (none/buffer/vector), vectorStoreId, retentionDays       |
| 6 | Channels & Guardrails | channelIds (WhatsApp/Telegram/Slack), schedule, maxStepsPerRun, maxCostUsd |
| 7 | Review         | read-only summary, "Create agent" button                               |

### Folder layout

```txt
modules/agent-creation/
  ui/
    AgentCreationPage.tsx
    AgentCreationStepper.tsx       # step index + nav
    AgentBasicsStep.tsx
    AgentLlmStep.tsx
    AgentPromptStep.tsx
    AgentToolsStep.tsx
    AgentMemoryStep.tsx
    AgentChannelsStep.tsx
    AgentReviewStep.tsx
  model/
    agent-creation.schema.ts       # per-step + merged schema
    agent-creation.store.ts        # current step, validation flags
  lib/
    map-form-to-create-agent-payload.ts
  index.ts
```

### One form, advance-by-validate

Use a single `useForm<CreateAgentInput>` instance. Each "Next" button calls `form.trigger(fieldsForCurrentStep)` and only advances if it returns true.

```tsx
const stepFields: Record<StepId, FieldPath<CreateAgentInput>[]> = {
  basics: ["name", "role"],
  llm:    ["providerId", "model", "temperature"],
  prompt: ["systemPrompt"],
  tools:  ["toolIds"],
  memory: ["memory"],
  channels: ["channelIds", "guardrails"],
};

async function goNext() {
  const ok = await form.trigger(stepFields[currentStep]);
  if (!ok) return;
  setCurrentStep(nextStep(currentStep));
}
```

### Final submit

```tsx
const onCreate = form.handleSubmit(async (input) => {
  const payload = mapFormToCreateAgentPayload(input);
  const agent = await createAgent.mutateAsync(payload);
  router.navigate(`/agents/${agent.id}`);
});
```

### Share the inner forms with the editor

`features/configure-llm`, `features/configure-tool`, `features/manage-memory`, and `features/connect-channel` should render the inputs for steps 2, 4, 5, 6 respectively. The stepper just composes them. See [[agent-feature-reuse]].

### Stepper state

The "which step am I on" is local UI state → Zustand store inside `agent-creation/model/`. The form values themselves stay in React Hook Form. Do not duplicate.

See: [[state-form-rhf-zod]], [[agent-editor-layout]], [[agent-feature-reuse]]
