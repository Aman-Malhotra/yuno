/** Status row returned by GET /llm-providers and GET /llm-providers/{p}/credentials. */
export type LlmCredentialStatus = {
  provider: string;
  isConfigured: boolean;
  baseUrl?: string;
  organization?: string;
  /** ISO timestamp of the last upsert. Null/undefined if never configured. */
  updatedAt?: string;
};

/** Body for POST /llm-providers/{provider}/credentials. */
export type SetLlmCredentialsInput = {
  apiKey: string;
  baseUrl?: string;
  organization?: string;
};
