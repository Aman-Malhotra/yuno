---
title: Realtime Run Events
impact: HIGH
impactDescription: Yuno requires live logs, inter-agent messages, and token/cost tracking — without a clean stream pipeline, the demo screen is dead
tags: realtime, sse, websocket, runs, monitoring
---

## Realtime Run Events

A run is a backend-driven execution. The frontend subscribes to a single normalized event stream per run and renders it in the run monitor and the agent test console.

### Event shape

```ts
// entities/run/model/run-event.types.ts
export type RunStatus =
  | "queued" | "running" | "waiting_human" | "succeeded" | "failed" | "cancelled";

export type RunEvent =
  | { type: "run.started"; runId: RunId; at: string }
  | { type: "run.status"; runId: RunId; status: RunStatus; at: string }
  | { type: "node.started"; runId: RunId; nodeId: NodeId; at: string }
  | { type: "node.finished"; runId: RunId; nodeId: NodeId; status: "ok" | "error"; at: string; durationMs: number }
  | { type: "agent.message"; runId: RunId; fromAgentId: AgentId; toAgentId: AgentId | null; content: string; at: string }
  | { type: "tool.invoked"; runId: RunId; nodeId: NodeId; toolName: string; arguments: unknown; at: string }
  | { type: "tool.returned"; runId: RunId; nodeId: NodeId; toolName: string; result: unknown; at: string }
  | { type: "llm.token"; runId: RunId; nodeId: NodeId; delta: string }
  | { type: "llm.usage"; runId: RunId; nodeId: NodeId; usage: { inputTokens: number; outputTokens: number; costUsd: number } }
  | { type: "channel.outbound"; runId: RunId; channel: "whatsapp" | "telegram" | "slack"; to: string; content: string; at: string }
  | { type: "channel.inbound"; runId: RunId; channel: "whatsapp" | "telegram" | "slack"; from: string; content: string; at: string }
  | { type: "log"; runId: RunId; level: "info" | "warn" | "error"; message: string; at: string }
  | { type: "run.error"; runId: RunId; error: string; at: string }
  | { type: "run.done"; runId: RunId; status: RunStatus; at: string };
```

### Prefer SSE over WebSocket for Yuno

The stream is one-way (backend → frontend), HTTP-friendly, survives proxies, and works with `fetch` + `ReadableStream`. Only use WebSocket if you also need client → server messages on the same channel (you don't — user actions are normal `POST`s).

### Client

```ts
// entities/run/realtime/run-events.client.ts
export function openRunEventStream(
  runId: RunId,
  onEvent: (e: RunEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const es = new EventSource(`/api/runs/${runId}/events`);
  es.onmessage = (msg) => onEvent(runEventSchema.parse(JSON.parse(msg.data)));
  signal?.addEventListener("abort", () => es.close());
  return new Promise((resolve, reject) => {
    es.addEventListener("done", () => { es.close(); resolve(); });
    es.onerror = (e) => { es.close(); reject(e); };
  });
}
```

### Hook that pushes events into TanStack Query cache

```ts
// features/inspect-run/api/useRunEventStream.ts
export function useRunEventStream(runId: RunId) {
  const qc = useQueryClient();

  useEffect(() => {
    const ac = new AbortController();
    openRunEventStream(
      runId,
      (event) => {
        qc.setQueryData(runQueryKeys.events(runId), (prev: RunEvent[] = []) => [...prev, event]);

        if (event.type === "run.status" || event.type === "run.done") {
          qc.setQueryData(runQueryKeys.detail(runId), (prev: Run | undefined) =>
            prev ? { ...prev, status: event.type === "run.done" ? event.status : event.status } : prev);
        }
      },
      ac.signal,
    );
    return () => ac.abort();
  }, [runId, qc]);
}
```

### Render targets

| Yuno requirement                  | Rendered from events                                   |
|-----------------------------------|--------------------------------------------------------|
| Real-time logs                    | `log`                                                  |
| Inter-agent messages              | `agent.message`                                        |
| Token/cost tracking               | sum of `llm.usage`                                     |
| Node-status overlay on canvas     | `node.started` / `node.finished`                       |
| Streaming chat in test console    | `llm.token` aggregated                                 |
| WhatsApp/Telegram/Slack transcript| `channel.inbound` / `channel.outbound`                 |

### Validate with Zod

Always parse incoming events with a Zod union. A malformed event must not crash the run monitor.

See: [[state-server-tanstack-query]], [[channel-integration-ui]]
