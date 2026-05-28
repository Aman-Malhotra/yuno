import { z } from "zod";
import { ApiService } from "@/shared/api";

import {
  credentialStatusWireSchema,
  credentialsListWireSchema,
  toCredentialStatus,
} from "../model/llm-provider.schema";
import type { LlmCredentialStatus, SetLlmCredentialsInput } from "../model/llm-provider.types";

/**
 * Mirrors `/api/v1/llm-providers/*` from openapi.yaml.
 *
 *   GET    /llm-providers/                            → list of credential statuses
 *   GET    /llm-providers/{provider}/credentials      → single status
 *   POST   /llm-providers/{provider}/credentials      → upsert (204)
 *   DELETE /llm-providers/{provider}/credentials      → revoke (204, idempotent)
 *
 * API keys are never echoed back — only `is_configured` + non-secret
 * metadata (base_url, organization, updated_at).
 */
class LlmProviderService extends ApiService {
  constructor() {
    super("/llm-providers");
  }

  list = async (): Promise<LlmCredentialStatus[]> => {
    const wire = await this._get("/", credentialsListWireSchema);
    return wire.items.map(toCredentialStatus);
  };

  getStatus = async (providerKey: string): Promise<LlmCredentialStatus> => {
    const wire = await this._get(`/${providerKey}/credentials`, credentialStatusWireSchema);
    return toCredentialStatus(wire);
  };

  registerCredential = async (providerKey: string, input: SetLlmCredentialsInput): Promise<void> => {
    await this._post(
      `/${providerKey}/credentials`,
      {
        api_key: input.apiKey,
        base_url: input.baseUrl,
        organization: input.organization,
      },
      z.void(),
    );
  };

  deleteCredential = async (providerKey: string): Promise<void> => {
    await this._delete(`/${providerKey}/credentials`, z.void());
  };
}

export const llmProviderApi = new LlmProviderService();
