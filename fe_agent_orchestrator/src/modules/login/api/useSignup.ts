import { useMutation } from "@tanstack/react-query";
import { clearAuth, setAuthTokens, setAuthUser, type AuthUser } from "@/app/auth";
import { authApi } from "./auth.service";
import type { SignupInput } from "../model/auth.schema";

/**
 * Signup mirrors login: create account → tokens → store tokens → /me →
 * overwrite user. Storing tokens BEFORE /me is essential, otherwise the
 * /me call has no Authorization header.
 */
export function useSignup() {
  return useMutation({
    mutationFn: async (input: SignupInput): Promise<AuthUser> => {
      const bundle = await authApi.signup(input);

      // Dev-only token log. Remove or guard with `import.meta.env.DEV` once
      // signup is verified end-to-end. Tokens never leave the browser; this
      // is just so you can copy/paste into curl or DevTools.
      // eslint-disable-next-line no-console
      console.groupCollapsed("[auth] signup → tokens received");
      // eslint-disable-next-line no-console
      console.log("accessToken         :", bundle.accessToken);
      // eslint-disable-next-line no-console
      console.log("refreshToken        :", bundle.refreshToken);
      // eslint-disable-next-line no-console
      console.log(
        "accessExpiresInSec  :",
        bundle.accessExpiresInSec,
        `(~${(bundle.accessExpiresInSec / 3600).toFixed(1)}h)`,
      );
      // eslint-disable-next-line no-console
      console.log(
        "refreshExpiresInSec :",
        bundle.refreshExpiresInSec,
        `(~${(bundle.refreshExpiresInSec / 86400).toFixed(1)}d)`,
      );
      // eslint-disable-next-line no-console
      console.log("accessExpiresAt     :", new Date(Date.now() + bundle.accessExpiresInSec * 1000).toISOString());
      // eslint-disable-next-line no-console
      console.log("refreshExpiresAt    :", new Date(Date.now() + bundle.refreshExpiresInSec * 1000).toISOString());
      // eslint-disable-next-line no-console
      console.groupEnd();

      const stubUser: AuthUser = {
        id: "pending",
        name: input.name,
        email: input.email,
        initials:
          input.name
            .split(/[\s._-]+/)
            .map((p) => p[0])
            .filter(Boolean)
            .slice(0, 2)
            .join("")
            .toUpperCase() || input.email.slice(0, 2).toUpperCase(),
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
