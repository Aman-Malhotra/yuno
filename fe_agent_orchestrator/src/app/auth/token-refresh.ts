import { authApi } from "@/modules/login/api/auth.service";
import { clearAuth, getAuthTokens, isAccessTokenExpired, setTokensOnly } from "./auth-token";

/**
 * Single-flight access-token refresh.
 *
 * - Re-uses the in-flight promise if multiple callers race
 * - Rotates BOTH tokens — /auth/refresh issues a fresh pair and revokes
 *   the old refresh token atomically (see openapi.yaml)
 * - Clears auth on failure (forces the user back to /login via the route
 *   guard's beforeLoad check)
 */
let inflight: Promise<string | null> | null = null;

export async function refreshAccessTokenIfNeeded(): Promise<string | null> {
  if (!isAccessTokenExpired()) {
    return getAuthTokens()?.accessToken ?? null;
  }
  return refreshAccessToken();
}

export async function refreshAccessToken(): Promise<string | null> {
  if (inflight) return inflight;

  const tokens = getAuthTokens();
  if (!tokens) return null;

  inflight = (async () => {
    try {
      const next = await authApi.refresh(tokens.refreshToken);
      setTokensOnly({
        accessToken: next.accessToken,
        refreshToken: next.refreshToken,
        accessExpiresAt: Date.now() + next.accessExpiresInSec * 1000,
        refreshExpiresAt: Date.now() + next.refreshExpiresInSec * 1000,
      });
      return next.accessToken;
    } catch {
      clearAuth();
      return null;
    } finally {
      inflight = null;
    }
  })();

  return inflight;
}
