import { z } from "zod";
import { env } from "@/app/config/env";
import { getAccessToken } from "@/app/auth/auth-token";
import { ApiError } from "./api-error";

/**
 * Every non-2xx response from the backend is `{ error: { code, message, details? } }`
 * (see openapi.yaml ErrorEnvelope). We unwrap it into ApiError so call sites
 * don't need to know about the envelope.
 */
const errorEnvelopeSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.record(z.string(), z.unknown()).optional(),
  }),
});

export async function httpRequest<T>(path: string, schema: z.ZodType<T>, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();

  const res = await fetch(`${env.API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
    credentials: "include",
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const parsed = errorEnvelopeSchema.safeParse(body);
    if (parsed.success) {
      throw new ApiError(parsed.data.error.message, res.status, parsed.data.error.code, parsed.data.error.details);
    }
    throw new ApiError(res.statusText || `HTTP ${res.status}`, res.status);
  }

  if (res.status === 204) return undefined as T;

  const json: unknown = await res.json();
  return schema.parse(json);
}
