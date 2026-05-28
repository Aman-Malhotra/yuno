import { z } from "zod";

export const runEventSchema = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("run.started"),
    runId: z.string(),
    at: z.string(),
  }),
  z.object({
    type: z.literal("run.status"),
    runId: z.string(),
    status: z.enum(["queued", "running", "waiting_human", "succeeded", "failed", "cancelled"]),
    at: z.string(),
  }),
  z.object({
    type: z.literal("node.started"),
    runId: z.string(),
    nodeId: z.string(),
    at: z.string(),
  }),
  z.object({
    type: z.literal("node.finished"),
    runId: z.string(),
    nodeId: z.string(),
    status: z.enum(["ok", "error"]),
    durationMs: z.number(),
    at: z.string(),
  }),
  z.object({
    type: z.literal("agent.message"),
    runId: z.string(),
    fromAgentId: z.string(),
    toAgentId: z.string().nullable(),
    content: z.string(),
    at: z.string(),
  }),
  z.object({
    type: z.literal("llm.usage"),
    runId: z.string(),
    nodeId: z.string(),
    usage: z.object({
      inputTokens: z.number(),
      outputTokens: z.number(),
      costUsd: z.number(),
    }),
  }),
  z.object({
    type: z.literal("channel.outbound"),
    runId: z.string(),
    channel: z.enum(["whatsapp", "telegram", "slack"]),
    to: z.string(),
    content: z.string(),
    at: z.string(),
  }),
  z.object({
    type: z.literal("channel.inbound"),
    runId: z.string(),
    channel: z.enum(["whatsapp", "telegram", "slack"]),
    from: z.string(),
    content: z.string(),
    at: z.string(),
  }),
  z.object({
    type: z.literal("log"),
    runId: z.string(),
    level: z.enum(["info", "warn", "error"]),
    message: z.string(),
    at: z.string(),
  }),
  z.object({
    type: z.literal("run.done"),
    runId: z.string(),
    status: z.enum(["succeeded", "failed", "cancelled"]),
    at: z.string(),
  }),
]);

export type RunEvent = z.infer<typeof runEventSchema>;
