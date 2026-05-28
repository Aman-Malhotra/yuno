---
title: Typed Fetch + Zod HTTP Client
impact: MEDIUM
impactDescription: Without Zod parsing at the boundary, a backend schema change becomes a runtime crash in the canvas
tags: api, http, fetch, zod
---

## Typed Fetch + Zod HTTP Client

Single thin wrapper around `fetch`. All response data is parsed through a Zod schema at the boundary. No `any` past the wrapper.

### Client

```ts
// shared/api/api-error.ts
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// shared/api/http-client.ts
import { z } from "zod";
import { env } from "@/app/config/env";
import { ApiError } from "./api-error";

const errorBodySchema = z.object({
  message: z.string(),
  code: z.string().optional(),
  details: z.unknown().optional(),
});

export async function httpRequest<T>(
  path: string,
  schema: z.ZodType<T>,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${env.API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
    credentials: "include",
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const parsed = errorBodySchema.safeParse(body);
    throw new ApiError(
      parsed.success ? parsed.data.message : res.statusText,
      res.status,
      parsed.success ? parsed.data.code : undefined,
      parsed.success ? parsed.data.details : undefined,
    );
  }

  if (res.status === 204) return undefined as T;

  const json = await res.json();
  return schema.parse(json);
}
```

### Per-entity API module

```ts
// entities/agent/api/agent.api.ts
import { z } from "zod";
import { httpRequest } from "@/shared/api/http-client";
import { agentSchema, type Agent, type AgentId, type CreateAgentInput } from "@/entities/agent";

const agentListSchema = z.array(agentSchema);

export const agentApi = {
  list: (filters: AgentFilters = {}) =>
    httpRequest(`/agents?${new URLSearchParams(filters as any)}`, agentListSchema),

  getById: (id: AgentId) =>
    httpRequest(`/agents/${id}`, agentSchema),

  create: (input: CreateAgentInput) =>
    httpRequest(`/agents`, agentSchema, {
      method: "POST",
      body: JSON.stringify(input),
    }),

  update: (id: AgentId, input: Partial<CreateAgentInput>) =>
    httpRequest(`/agents/${id}`, agentSchema, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),

  delete: (id: AgentId) =>
    httpRequest(`/agents/${id}`, z.void(), { method: "DELETE" }),
};
```

### Bad

```ts
// ❌ no validation, returns `any`, every consumer guesses the shape
const res = await fetch(`/agents/${id}`);
const data = await res.json();
return data;
```

### Good

```ts
// ✅ shape is enforced, errors throw `ApiError` with status
const agent = await httpRequest(`/agents/${id}`, agentSchema);
```

See: [[api-query-keys]], [[ts-strict]]
