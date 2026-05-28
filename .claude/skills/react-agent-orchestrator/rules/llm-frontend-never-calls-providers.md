---
title: Frontend Never Calls LLM Providers Directly
impact: CRITICAL
impactDescription: Shipping an OpenAI/Anthropic key to the browser leaks it to every user; tool execution, billing, and rate limiting also belong server-side
tags: llm, security, boundaries
---

## Frontend Never Calls LLM Providers Directly

The React app **must not** import or call `openai`, `@anthropic-ai/sdk`, `@google/genai`, `groq-sdk`, or any other provider SDK from the browser. Every model call goes through our backend.

### Why

- **API keys leak.** Anything in the browser bundle is public.
- **Tool execution is server-controlled.** Tools run in the runtime (LangGraph/CrewAI/AutoGen), not the browser.
- **Billing, rate limits, retries, tracing** belong to the backend.
- **Provider switching** stays a backend-only change.

### What the frontend may do

- Render UI to **configure** providers (model select, temperature sliders)
- Read model lists / capabilities via our backend API
- Open an SSE/WebSocket stream to a backend-controlled run
- Show token usage and cost coming from backend events

### What the frontend may NOT do

```ts
// ❌ NEVER
import OpenAI from "openai";
const client = new OpenAI({ apiKey: import.meta.env.VITE_OPENAI_KEY });
await client.chat.completions.create({ /* ... */ });
```

```ts
// ❌ NEVER — even with dangerouslyAllowBrowser
import Anthropic from "@anthropic-ai/sdk";
new Anthropic({ apiKey: "...", dangerouslyAllowBrowser: true });
```

### What the frontend does instead

```ts
// features/test-agent/api/useTestAgent.ts
export function useTestAgent(agentId: AgentId) {
  return useMutation({
    mutationFn: (input: { message: string }) =>
      httpRequest(`/agents/${agentId}/test-runs`, runStartedSchema, {
        method: "POST",
        body: JSON.stringify(input),
      }),
  });
}
```

```ts
// LLM playground talks to a backend route, not OpenAI directly
const stream = openRunEventStream(`/runs/${runId}/events`);
```

### Provider config UI — frontend territory

```ts
// entities/llm-provider/model/llm-provider.types.ts
export type LlmProviderName =
  | "openai"
  | "anthropic"
  | "gemini"
  | "groq"
  | "mistral"
  | "deepseek"
  | "ollama"
  | "custom_openai_compatible";

export type LlmProviderConfig = {
  id: string;
  name: string;
  provider: LlmProviderName;
  displayName: string;
  isEnabled: boolean;
  models: LlmModel[];
  capabilities: {
    streaming: boolean;
    tools: boolean;
    jsonMode: boolean;
    vision: boolean;
    audio: boolean;
  };
};
```

The user types/pastes an API key into a form → it `POST`s to `/providers/:id/credentials` → the backend stores it encrypted. The key never round-trips back to the client.

### Bundle check

Add to CI: `pnpm why openai`, `pnpm why @anthropic-ai/sdk` etc. should report nothing in the frontend workspace.

See: [[llm-backend-interface]], [[realtime-run-events]]
