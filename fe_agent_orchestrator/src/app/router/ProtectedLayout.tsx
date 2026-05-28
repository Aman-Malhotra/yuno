import { useEffect } from "react";
import { Outlet, useNavigate, useRouterState } from "@tanstack/react-router";

import { clearAuth, setAuthUser, useAuth, useTokenRefreshSchedule } from "@/app/auth";
import { DashboardLayout } from "@/modules/dashboard";
import { useCurrentUser } from "@/modules/login/api/useCurrentUser";
import { Brand } from "@/shared/ui";

/**
 * Wraps every authenticated route. Four layers of guard:
 *
 * 1. The route's `beforeLoad` already bounced unauthenticated users at
 *    navigation time (no token → /login).
 * 2. `useCurrentUser` calls GET /auth/me to ask the backend whether the
 *    bearer token is still valid. If the call errors (401, expired, etc.)
 *    we clear auth and bounce to /login.
 * 3. `useTokenRefreshSchedule` rotates the access token ~60s before it
 *    expires so the user never sees a 401 mid-session.
 * 4. We watch `isAuthenticated` — the moment it goes false (sign-out
 *    button, another tab signed out, manual localStorage clear, refresh
 *    failure) we navigate to /login without waiting for a route change.
 */
export function ProtectedLayout() {
  useTokenRefreshSchedule();
  const me = useCurrentUser();
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useRouterState({ select: (s) => s.location });

  // Keep the cached user in sync with the server's source of truth.
  useEffect(() => {
    if (me.data) setAuthUser(me.data);
  }, [me.data]);

  // /me rejected → drop the session.
  useEffect(() => {
    if (me.isError) {
      clearAuth();
    }
  }, [me.isError]);

  // Whenever the session is gone for ANY reason, leave the protected tree.
  useEffect(() => {
    if (!isAuthenticated) {
      void navigate({
        to: "/login",
        search: { redirect: location.href },
        replace: true,
      });
    }
  }, [isAuthenticated, navigate, location.href]);

  if (!isAuthenticated) return null;

  if (me.isPending) {
    return (
      <div className="grid min-h-screen place-items-center">
        <div className="flex flex-col items-center gap-3 text-ink-mute">
          <Brand />
          <span className="font-mono text-[10px] uppercase tracking-eyebrow">Verifying session…</span>
        </div>
      </div>
    );
  }

  if (me.isError || !me.data) return null;

  return (
    <DashboardLayout>
      <Outlet />
    </DashboardLayout>
  );
}
