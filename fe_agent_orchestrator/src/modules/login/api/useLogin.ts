import { useMutation } from "@tanstack/react-query";
import { clearAuth, setAuthTokens, setAuthUser, type AuthUser } from "@/app/auth";
import { authApi } from "./auth.service";
import type { LoginInput } from "../model/auth.schema";

/**
 * Login flow:
 *   1. POST /auth/login  → get tokens
 *   2. Save tokens to localStorage IMMEDIATELY so the http-client picks them
 *      up for the next request. (Skip this and /me goes out with no
 *      Authorization header → 401 "auth required".)
 *   3. GET /auth/me      → server-side validate + populate the user
 *   4. Persist the user. If /me throws, roll back so we don't leave dangling
 *      tokens that the protected layout would happily accept.
 */
export function useLogin() {
  return useMutation({
    mutationFn: async (input: LoginInput): Promise<AuthUser> => {
      const bundle = await authApi.login(input);

      const stubUser: AuthUser = {
        id: "pending",
        name: "",
        email: input.email,
        initials: input.email.slice(0, 2).toUpperCase(),
      };
      setAuthTokens(
        {
          accessToken: bundle.accessToken,
          refreshToken: bundle.refreshToken,
          accessExpiresAt: Date.now() + bundle.accessExpiresInSec * 1000,
          refreshExpiresAt: Date.now() + bundle.refreshExpiresInSec * 1000,
        },
        stubUser,
      );

      try {
        const user = await authApi.me();
        setAuthUser(user);
        return user;
      } catch (err) {
        clearAuth();
        throw err;
      }
    },
  });
}
