import { z } from "zod";

/**
 * Mirrors CreateAgentRequest in openapi.yaml. The five required fields are
 * the minimum LangGraph needs to materialise the node; everything else is
 * either optional or has a server-side default.
 *
 * `providerApiKey` is a frontend-only field — it gets posted to the
 * provider-credentials endpoint *before* the agent is created. It's never
 * sent in the CreateAgentRequest body.
 *
 * `toolSlugs` is also frontend-only — the service serialises it into
 * `skills_config.tools` per ToolEntryShape before POSTing.
 *
 * The five ``…Json`` fields are stringified JSONB blocks: the form holds
 * raw text so users can edit free-form, and the submit handler parses
 * them. `maxToolHops` is a convenience field that gets merged into
 * `guardrailsConfig.max_tool_hops` on save.
 */
export const createAgentSchema = z.object({
  name: z.string().trim().min(1, "Name is required").max(255, "Max 255 characters"),
  role: z.string().trim().min(1, "Role is required").max(120, "Max 120 characters"),
  systemPrompt: z.string().trim().min(1, "System prompt is required"),
  modelProvider: z.string().trim().min(1, "Pick a provider"),
  modelName: z.string().trim().min(1, "Pick a model"),
  description: z.string().trim().max(2000).optional().or(z.literal("")),
  temperature: z.number().min(0).max(2),
  maxTokens: z.number().int().min(1).max(128_000).optional(),
  providerApiKey: z.string().optional(),
  toolSlugs: z.array(z.string()),

  // ── Runtime knobs ───────────────────────────────────────────────
  // Typed shortcut — merged into guardrails_config.max_tool_hops on save.
  // Caps the agent's tool-calling loop inside a single turn.
  maxToolHops: z.number().int().min(0).max(20).optional(),

  // Raw JSON for the five JSONB config blocks. Each must parse to an
  // object — anything else is rejected before submit so the server sees
  // the right shape.
  memoryConfigJson: z.string(),
  scheduleConfigJson: z.string(),
  guardrailsConfigJson: z.string(),
  interactionRulesJson: z.string(),
  limitsConfigJson: z.string(),
});

export type CreateAgentFormValues = z.infer<typeof createAgentSchema>;
