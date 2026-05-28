import { env } from "@/app/config/env";
import { runEventSchema, type RunEvent } from "../model/run-event.types";
import type { RunId } from "../model/run.types";

export function openRunEventStream(runId: RunId, onEvent: (e: RunEvent) => void, signal?: AbortSignal): () => void {
  const es = new EventSource(`${env.API_BASE_URL}/runs/${runId}/events`);

  es.onmessage = (msg) => {
    try {
      const parsed = runEventSchema.parse(JSON.parse(msg.data));
      onEvent(parsed);
    } catch (err) {
      console.warn("malformed run event", err);
    }
  };

  es.addEventListener("done", () => es.close());
  es.onerror = () => es.close();

  const close = () => es.close();
  signal?.addEventListener("abort", close);
  return close;
}
