import { z } from "zod";
import type { AgentId } from "@/entities/agent";
import type { AgentCostRow, CostsSummary } from "./cost.types";

const agentIdSchema = z
  .string()
  .min(1)
  .transform((s) => s as AgentId);

const agentCostWireSchema = z.object({
  agent_id: agentIdSchema,
  name: z.string(),
  slug: z.string(),
  model_provider: z.string(),
  model_name: z.string(),
  input_tokens: z.number(),
  output_tokens: z.number(),
  total_tokens: z.number(),
  run_count: z.number(),
  last_seen_at: z.string().nullable().optional(),
});

export const costsResponseWireSchema = z.object({
  items: z.array(agentCostWireSchema),
  total_input_tokens: z.number(),
  total_output_tokens: z.number(),
  total_tokens: z.number(),
});

export function toAgentCostRow(w: z.infer<typeof agentCostWireSchema>): AgentCostRow {
  return {
    agentId: w.agent_id,
    name: w.name,
    slug: w.slug,
    modelProvider: w.model_provider,
    modelName: w.model_name,
    inputTokens: w.input_tokens,
    outputTokens: w.output_tokens,
    totalTokens: w.total_tokens,
    runCount: w.run_count,
    lastSeenAt: w.last_seen_at ?? undefined,
  };
}

export function toCostsSummary(w: z.infer<typeof costsResponseWireSchema>): CostsSummary {
  return {
    items: w.items.map(toAgentCostRow),
    totalInputTokens: w.total_input_tokens,
    totalOutputTokens: w.total_output_tokens,
    totalTokens: w.total_tokens,
  };
}
