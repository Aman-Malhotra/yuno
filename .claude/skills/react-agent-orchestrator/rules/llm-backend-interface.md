---
title: Backend LlmProvider Interface
impact: HIGH
impactDescription: One interface keeps OpenAI/Anthropic/Gemini/Groq/Ollama swappable; without it, agent runtime code branches on provider name everywhere
tags: llm, backend, interface, adapter
---

## Backend LlmProvider Interface

This rule documents the backend boundary the frontend talks to. Frontend code never imports these types directly, but knowing the shape clarifies what to display and configure.

### Core types

```ts
export type LlmProviderName =
  | "openai" | "anthropic" | "gemini" | "groq"
  | "mistral" | "deepseek" | "ollama" | "custom_openai_compatible";

export type LlmMessage = {
  role: "system" | "user" | "assistant" | "tool";
  content: string;
  name?: string;
  toolCallId?: string;
};

export type LlmToolDefinition = {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>; // JSON Schema
};

export type LlmToolCall = {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
};

export type LlmCompletionRequest = {
  model: string;
  messages: LlmMessage[];
  temperature?: number;
  maxTokens?: number;
  tools?: LlmToolDefinition[];
  responseFormat?: "text" | "json";
  metadata?: Record<string, unknown>;
};

export type LlmUsage = {
  inputTokens?: number;
  outputTokens?: number;
  totalTokens?: number;
  costUsd?: number;
};

export type LlmCompletionResponse = {
  id: string;
  provider: LlmProviderName;
  model: string;
  content: string;
  toolCalls?: LlmToolCall[];
  usage?: LlmUsage;
  raw?: unknown;
};

export type LlmStreamEvent =
  | { type: "token"; value: string }
  | { type: "tool_call"; value: LlmToolCall }
  | { type: "usage"; value: LlmUsage }
  | { type: "done" }
  | { type: "error"; error: string };

export interface LlmProvider {
  readonly name: LlmProviderName;
  complete(req: LlmCompletionRequest): Promise<LlmCompletionResponse>;
  stream(req: LlmCompletionRequest): AsyncIterable<LlmStreamEvent>;
  listModels(): Promise<LlmModel[]>;
  validateConfig(config: unknown): Promise<boolean>;
}
```

### Backend folder

```txt
backend/src/llm/
  core/
    llm-provider.interface.ts
    llm.types.ts
    llm.errors.ts
    llm-registry.ts
  providers/
    openai/openai.provider.ts
    anthropic/anthropic.provider.ts
    gemini/gemini.provider.ts
    groq/groq.provider.ts
    mistral/mistral.provider.ts
    deepseek/deepseek.provider.ts
    ollama/ollama.provider.ts
    custom-openai-compatible/custom-openai-compatible.provider.ts
```

### Registry

```ts
export class LlmProviderRegistry {
  private readonly providers = new Map<LlmProviderName, LlmProvider>();

  register(p: LlmProvider) { this.providers.set(p.name, p); }

  get(name: LlmProviderName): LlmProvider {
    const p = this.providers.get(name);
    if (!p) throw new Error(`LLM provider not registered: ${name}`);
    return p;
  }
}
```

### What the frontend mirrors

The frontend only needs:

```ts
// entities/llm-provider/model/llm-provider.types.ts
export type LlmProviderConfig = {
  id: string;
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

These come from `GET /providers` — backend returns provider configs with credentials stripped.

### Stream events flow to the frontend

`LlmStreamEvent` from the backend → bridged through the runtime → emitted on the run's SSE channel as `RunEvent` records ([[realtime-run-events]]). The frontend never sees raw provider tokens; it sees normalized `RunEvent`s.

See: [[llm-frontend-never-calls-providers]], [[realtime-run-events]]
