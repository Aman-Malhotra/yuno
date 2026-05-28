import { z } from "zod";
import { ApiService } from "@/shared/api";
import type { AuthUser } from "@/app/auth";
import type { LoginInput, SignupInput } from "../model/auth.schema";

/* ─── Wire schemas — match openapi.yaml exactly (snake_case) ────── */

const tokenResponseSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.literal("bearer").optional(),
  expires_in: z.number(),
  refresh_expires_in: z.number(),
});

const currentUserResponseSchema = z.object({
  id: z.string(),
  email: z.string(),
  full_name: z.string().nullable().optional(),
  avatar_url: z.string().nullable().optional(),
  is_active: z.boolean(),
  is_verified: z.boolean(),
  created_at: z.string(),
});

/* ─── Domain shapes used by the rest of the app (camelCase) ─────── */

export type AuthBundle = {
  accessToken: string;
  refreshToken: string;
  accessExpiresInSec: number;
  refreshExpiresInSec: number;
};

/* ─── Mappers (wire → domain) ───────────────────────────────────── */

function toAuthBundle(t: z.infer<typeof tokenResponseSchema>): AuthBundle {
  return {
    accessToken: t.access_token,
    refreshToken: t.refresh_token,
    accessExpiresInSec: t.expires_in,
    refreshExpiresInSec: t.refresh_expires_in,
  };
}

function toAuthUser(u: z.infer<typeof currentUserResponseSchema>): AuthUser {
  const name = (u.full_name?.trim() || u.email.split("@")[0] || u.email).trim();
  const initials =
    name
      .split(/[\s._-]+/)
      .map((p) => p[0])
      .filter(Boolean)
      .slice(0, 2)
      .join("")
      .toUpperCase() || "OP";
  return {
    id: u.id,
    name,
    email: u.email,
    initials,
    createdAt: u.created_at,
    avatarUrl: u.avatar_url ?? null,
  };
}

/* ─── Service ───────────────────────────────────────────────────── */

class AuthService extends ApiService {
  constructor() {
    super("/auth");
  }

  login = async (input: LoginInput): Promise<AuthBundle> => {
    const wire = await this._post("/login", { email: input.email, password: input.password }, tokenResponseSchema);
    return toAuthBundle(wire);
  };

  signup = async (input: SignupInput): Promise<AuthBundle> => {
    const wire = await this._post(
      "/signup",
      { email: input.email, password: input.password, full_name: input.name },
      tokenResponseSchema,
    );
    return toAuthBundle(wire);
  };

  refresh = async (refreshToken: string): Promise<AuthBundle> => {
    const wire = await this._post("/refresh", { refresh_token: refreshToken }, tokenResponseSchema);
    return toAuthBundle(wire);
  };

  logout = async (refreshToken: string): Promise<void> => {
    await this._post("/logout", { refresh_token: refreshToken }, z.void());
  };

  /** Validates the current bearer token server-side and returns the user. */
  me = async (): Promise<AuthUser> => {
    const wire = await this._get("/me", currentUserResponseSchema);
    return toAuthUser(wire);
  };
}

export const authApi = new AuthService();
