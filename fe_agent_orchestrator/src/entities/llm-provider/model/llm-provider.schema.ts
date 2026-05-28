import { z } from "zod";
import type { LlmCredentialStatus } from "./llm-provider.types";

const credentialStatusWireSchema = z.object({
  provider: z.string(),
  is_configured: z.boolean(),
  base_url: z.string().nullable().optional(),
  organization: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
});

export function toCredentialStatus(s: z.infer<typeof credentialStatusWireSchema>): LlmCredentialStatus {
  return {
    provider: s.provider,
    isConfigured: s.is_configured,
    baseUrl: s.base_url ?? undefined,
    organization: s.organization ?? undefined,
    updatedAt: s.updated_at ?? undefined,
  };
}

export const credentialsListWireSchema = z.object({
  items: z.array(credentialStatusWireSchema),
});

export { credentialStatusWireSchema };
