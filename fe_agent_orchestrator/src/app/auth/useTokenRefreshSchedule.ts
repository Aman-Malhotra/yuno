import { useEffect } from "react";
import { useAuth } from "./useAuth";
import { refreshAccessToken } from "./token-refresh";

const REFRESH_LEAD_MS = 60_000; // refresh 60s before expiry

/**
 * Mount once at the top of the protected app. While logged in, schedules a
 * single timer to refresh the access token slightly before it expires. The
 * timer re-arms after each successful refresh because `accessExpiresAt`
 * changes in storage and the `useAuth` snapshot updates.
 */
export function useTokenRefreshSchedule(): void {
  const { accessExpiresAt, isAuthenticated } = useAuth();

  useEffect(() => {
    if (!isAuthenticated || !accessExpiresAt) return;

    const delay = Math.max(0, accessExpiresAt - Date.now() - REFRESH_LEAD_MS);
    const id = window.setTimeout(() => {
      void refreshAccessToken();
    }, delay);

    return () => window.clearTimeout(id);
  }, [accessExpiresAt, isAuthenticated]);
}
