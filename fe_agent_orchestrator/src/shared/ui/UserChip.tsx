import { Link } from "@tanstack/react-router";
import type { AuthUser } from "@/app/auth";
import { cn } from "@/shared/lib/cn";

type UserChipProps = {
  user: AuthUser;
  to?: string;
  className?: string;
};

/**
 * Header chip — links to the user's profile page by default. Profile page
 * is the only place the sign-out button lives, so clicking the chip never
 * silently signs people out.
 */
export function UserChip({ user, to = "/profile", className }: UserChipProps) {
  return (
    <Link
      to={to}
      className={cn(
        "group inline-flex items-center gap-2.5 rounded-sm border border-canvas-ruleStrong",
        "bg-canvas-panel px-2 py-1 transition-colors hover:border-sodium",
        className,
      )}
      title={user.email}
    >
      <span
        aria-hidden
        className="flex h-6 w-6 items-center justify-center rounded-sm border border-sodium/50 bg-sodium-tint font-mono text-[10px] font-medium text-sodium"
      >
        {user.initials}
      </span>
      <span className="flex flex-col items-start leading-none">
        <span className="text-[11px] text-ink">{user.name || user.email.split("@")[0]}</span>
        <span className="font-mono text-[9px] tracking-eyebrow text-ink-mute">{user.email}</span>
      </span>
    </Link>
  );
}
