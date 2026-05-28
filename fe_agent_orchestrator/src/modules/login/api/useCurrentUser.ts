import { useQuery } from "@tanstack/react-query";
import { authApi } from "./auth.service";
import type { AuthUser } from "@/app/auth";

export const authQueryKeys = {
  all: ["auth"] as const,
  me: () => [...authQueryKeys.all, "me"] as const,
} as const;

/**
 * Validates the current access token by asking the backend who it belongs
 * to. Mounted at the top of the protected layout — navigating into any
 * authenticated route requires a real server-side check.
 *
 * Behaviour:
 * - On success: caches the user for 5 min, revalidates on window focus
 * - On error (401/expired/anything): does NOT retry. The protected layout
 *   reacts by clearing auth + redirecting to /login.
 */
export function useCurrentUser() {
  return useQuery<AuthUser>({
    queryKey: authQueryKeys.me(),
    queryFn: () => authApi.me(),
    retry: 0,
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: true,
  });
}
