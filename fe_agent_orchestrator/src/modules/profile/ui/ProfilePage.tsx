import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { LogOut } from "lucide-react";

import { clearAuth, getRefreshToken, useAuth } from "@/app/auth";
import { authApi } from "@/modules/login/api/auth.service";
import { Button, Chip, SectionHeader } from "@/shared/ui";
import { cn } from "@/shared/lib/cn";

function formatJoined(iso?: string): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[140px_1fr] items-center gap-4 border-b border-canvas-rule py-3 last:border-b-0">
      <span className="eyebrow">{label}</span>
      <span className="text-sm text-ink">{value}</span>
    </div>
  );
}

export function ProfilePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [signingOut, setSigningOut] = useState(false);

  if (!user) return null;

  const onSignOut = async () => {
    setSigningOut(true);
    const rt = getRefreshToken();
    if (rt) {
      try {
        await authApi.logout(rt);
      } catch {
        // ignore — local clear below still logs them out
      }
    }
    clearAuth();
    void navigate({ to: "/login", search: { redirect: undefined }, replace: true });
  };

  return (
    <div className="mx-auto w-full max-w-2xl px-6 py-8">
      <SectionHeader
        eyebrow="Account"
        title={
          <>
            Your <span className="font-thin text-ink-dim">profile</span>
          </>
        }
        meta="Account details and sign-out."
      />

      <div className="hairline-x mt-6" />

      {/* Identity card */}
      <section className="mt-6 rounded-md border border-canvas-rule bg-canvas-panel p-6">
        <header className="flex items-start gap-4">
          <span
            aria-hidden
            className="flex h-14 w-14 items-center justify-center rounded-md border border-sodium/50 bg-sodium-tint font-mono text-base font-medium text-sodium"
          >
            {user.initials}
          </span>
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-lg font-medium text-ink">{user.name || user.email.split("@")[0]}</h2>
            <p className="truncate text-sm text-ink-dim">{user.email}</p>
          </div>
        </header>

        <div className="mt-6">
          <DetailRow label="User ID" value={<code className="font-mono text-xs text-ink-dim">{user.id}</code>} />
          <DetailRow label="Email" value={user.email} />
          <DetailRow label="Member since" value={formatJoined(user.createdAt)} />
        </div>
      </section>

      {/* Session card */}
      <section className="mt-6 rounded-md border border-canvas-rule bg-canvas-panel p-6">
        <header className="flex items-baseline justify-between">
          <div>
            <h3 className="text-sm font-medium text-ink">Session</h3>
            <p className="mt-1 text-xs text-ink-dim">
              Signing out revokes the refresh token server-side and clears local storage.
            </p>
          </div>
          <Chip tone="default">this device</Chip>
        </header>

        <div className="mt-4 flex items-center justify-end">
          <Button
            type="button"
            variant="danger"
            onClick={onSignOut}
            disabled={signingOut}
            className={cn(signingOut && "opacity-70")}
          >
            <LogOut size={14} strokeWidth={1.8} />
            {signingOut ? "Signing out…" : "Sign out"}
          </Button>
        </div>
      </section>
    </div>
  );
}
