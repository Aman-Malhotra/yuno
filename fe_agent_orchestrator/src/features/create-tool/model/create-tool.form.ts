import { z } from "zod";

const toolTypeEnum = z.enum(["builtin", "http", "messaging", "agent_handoff", "webhook", "python", "mock"]);

const toolStatusEnum = z.enum(["draft", "active", "disabled", "archived"]);

function validateJsonObject(raw: string | undefined, label: string, ctx: z.RefinementCtx, path: string) {
  if (!raw || !raw.trim()) return;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
      ctx.addIssue({
        code: "custom",
        message: `${label} must be a JSON object (e.g. { "type": "object", ... }).`,
        path: [path],
      });
    }
  } catch {
    ctx.addIssue({ code: "custom", message: `${label} is not valid JSON.`, path: [path] });
  }
}

/**
 * Mirrors the v1 subset of CreateToolRequest from openapi.yaml. Advanced
 * blobs (auth, guardrails, execution_policy, channels) are deliberately
 * skipped here — they're edited via the detail page once a tool exists.
 */
export const createToolSchema = z
  .object({
    name: z.string().trim().min(1, "Name is required").max(255, "Max 255 characters"),
    description: z.string().trim().min(1, "Description is required"),
    type: toolTypeEnum,
    category: z.string().trim().max(64).optional().or(z.literal("")),
    icon: z.string().trim().max(120).optional().or(z.literal("")),
    status: toolStatusEnum,
    inputSchemaRaw: z.string().trim().optional(),
    outputSchemaRaw: z.string().trim().optional(),
    configRaw: z.string().trim().optional(),
    publishNewVersion: z.boolean().optional(),
  })
  .superRefine((v, ctx) => {
    validateJsonObject(v.inputSchemaRaw, "Input schema", ctx, "inputSchemaRaw");
    validateJsonObject(v.outputSchemaRaw, "Output schema", ctx, "outputSchemaRaw");
    validateJsonObject(v.configRaw, "Config", ctx, "configRaw");
  });

export type CreateToolFormValues = z.infer<typeof createToolSchema>;
