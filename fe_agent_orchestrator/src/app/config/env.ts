import { z } from "zod";

/**
 * Single source of truth for runtime configuration.
 *
 * Backend API is versioned (`/api/v1/*`), so we bake `/api/v1` into the base
 * URL — services just declare their resource (`/auth`, `/agents`, etc.) and
 * never spell the version out.
 *
 * Override the URL at build time with `VITE_API_BASE_URL=https://api.yuno.com/api/v1`.
 * In local dev we keep it relative so the Vite proxy (vite.config.ts) can
 * forward `/api/*` to the backend on http://localhost:3001.
 */
const envSchema = z.object({
  API_BASE_URL: z.string().min(1).default("/api/v1"),
});

export const env = envSchema.parse({
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
});
