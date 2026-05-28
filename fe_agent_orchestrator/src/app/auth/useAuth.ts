import { useSyncExternalStore } from "react";
import { clearAuth, type AuthUser } from "./auth-token";

type AuthSnapshot = {
  accessToken: string | null;
  refreshToken: string | null;
  accessExpiresAt: number | null;
  refreshExpiresAt: number | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
};

const ACCESS_KEY = "yuno_access_token";
const REFRESH_KEY = "yuno_refresh_token";
const ACCESS_EXP_KEY = "yuno_access_expires_at";
const REFRESH_EXP_KEY = "yuno_refresh_expires_at";
const USER_KEY = "yuno_auth_user";

/**
 * useSyncExternalStore requires getSnapshot to return a STABLE reference
 * when nothing has changed. Cache the snapshot by a primitive key derived
 * from localStorage; only rebuild the object when that key changes.
 */
let cachedKey = "";
let cachedSnapshot: AuthSnapshot = {
  accessToken: null,
  refreshToken: null,
  accessExpiresAt: null,
  refreshExpiresAt: null,
  user: null,
  isAuthenticated: false,
};

function parseNumber(raw: string | null): number | null {
  if (!raw) return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

function getSnapshot(): AuthSnapshot {
  if (typeof window === "undefined") return cachedSnapshot;

  const access = window.localStorage.getItem(ACCESS_KEY);
  const refresh = window.localStorage.getItem(REFRESH_KEY);
  const accessExpRaw = window.localStorage.getItem(ACCESS_EXP_KEY);
  const refreshExpRaw = window.localStorage.getItem(REFRESH_EXP_KEY);
  const userRaw = window.localStorage.getItem(USER_KEY);
  const key = `${access ?? ""}|${refresh ?? ""}|${accessExpRaw ?? ""}|${refreshExpRaw ?? ""}|${userRaw ?? ""}`;

  if (key === cachedKey) return cachedSnapshot;

  cachedKey = key;
  let user: AuthUser | null = null;
  if (userRaw) {
    try {
      user = JSON.parse(userRaw) as AuthUser;
    } catch {
      user = null;
    }
  }
  cachedSnapshot = {
    accessToken: access,
    refreshToken: refresh,
    accessExpiresAt: parseNumber(accessExpRaw),
    refreshExpiresAt: parseNumber(refreshExpRaw),
    user,
    isAuthenticated: Boolean(access && user),
  };
  return cachedSnapshot;
}

function subscribe(cb: () => void): () => void {
  const onStorage = (e: StorageEvent) => {
    if (e.key === null || e.key.startsWith("yuno_")) cb();
  };
  const onLocal = () => cb();
  window.addEventListener("storage", onStorage);
  window.addEventListener("yuno_auth_change", onLocal);
  return () => {
    window.removeEventListener("storage", onStorage);
    window.removeEventListener("yuno_auth_change", onLocal);
  };
}

export function useAuth(): AuthSnapshot & { signOut: () => void } {
  const snap = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  return {
    ...snap,
    signOut: () => clearAuth(),
  };
}
