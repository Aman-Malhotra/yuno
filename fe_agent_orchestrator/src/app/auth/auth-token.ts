const ACCESS_KEY = "yuno_access_token";
const REFRESH_KEY = "yuno_refresh_token";
const ACCESS_EXP_KEY = "yuno_access_expires_at";
const REFRESH_EXP_KEY = "yuno_refresh_expires_at";
const USER_KEY = "yuno_auth_user";

export type AuthUser = {
  id: string;
  name: string;
  email: string;
  initials: string;
  /** ISO timestamp — populated when /auth/me returns it. */
  createdAt?: string;
  avatarUrl?: string | null;
};

export type TokenSet = {
  accessToken: string;
  refreshToken: string;
  /** ms-epoch when the access token expires (login: ~12h from now). */
  accessExpiresAt: number;
  /** ms-epoch when the refresh token expires (login: ~30d from now). */
  refreshExpiresAt: number;
};

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_KEY);
}

export function getAccessExpiresAt(): number | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(ACCESS_EXP_KEY);
  if (!raw) return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

export function getRefreshExpiresAt(): number | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(REFRESH_EXP_KEY);
  if (!raw) return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

export function getAuthTokens(): TokenSet | null {
  const accessToken = getAccessToken();
  const refreshToken = getRefreshToken();
  const accessExpiresAt = getAccessExpiresAt();
  const refreshExpiresAt = getRefreshExpiresAt();
  if (!accessToken || !refreshToken || !accessExpiresAt || !refreshExpiresAt) return null;
  return { accessToken, refreshToken, accessExpiresAt, refreshExpiresAt };
}

export function getAuthUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function isAccessTokenExpired(bufferMs = 60_000): boolean {
  const expiresAt = getAccessExpiresAt();
  if (!expiresAt) return true;
  return Date.now() >= expiresAt - bufferMs;
}

export function isRefreshTokenExpired(): boolean {
  const expiresAt = getRefreshExpiresAt();
  if (!expiresAt) return true;
  return Date.now() >= expiresAt;
}

function notifyAuthChanged(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event("yuno_auth_change"));
}

export function setAuthTokens(tokens: TokenSet, user: AuthUser): void {
  window.localStorage.setItem(ACCESS_KEY, tokens.accessToken);
  window.localStorage.setItem(REFRESH_KEY, tokens.refreshToken);
  window.localStorage.setItem(ACCESS_EXP_KEY, String(tokens.accessExpiresAt));
  window.localStorage.setItem(REFRESH_EXP_KEY, String(tokens.refreshExpiresAt));
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  notifyAuthChanged();
}

/**
 * Replace just the token pair (e.g. after /auth/refresh, which rotates the
 * refresh token too). User is unchanged.
 */
export function setTokensOnly(tokens: TokenSet): void {
  window.localStorage.setItem(ACCESS_KEY, tokens.accessToken);
  window.localStorage.setItem(REFRESH_KEY, tokens.refreshToken);
  window.localStorage.setItem(ACCESS_EXP_KEY, String(tokens.accessExpiresAt));
  window.localStorage.setItem(REFRESH_EXP_KEY, String(tokens.refreshExpiresAt));
  notifyAuthChanged();
}

export function setAuthUser(user: AuthUser): void {
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  notifyAuthChanged();
}

export function clearAuth(): void {
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
  window.localStorage.removeItem(ACCESS_EXP_KEY);
  window.localStorage.removeItem(REFRESH_EXP_KEY);
  window.localStorage.removeItem(USER_KEY);
  notifyAuthChanged();
}
