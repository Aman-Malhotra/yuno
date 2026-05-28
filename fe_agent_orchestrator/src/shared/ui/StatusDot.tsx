import { cn } from "@/shared/lib/cn";

type StatusDotProps = {
  state: "ok" | "warn" | "err" | "idle";
  pulse?: boolean;
  className?: string;
};

const colors: Record<StatusDotProps["state"], string> = {
  ok: "bg-signal-ok shadow-[0_0_6px_rgba(47,138,78,0.5)]",
  warn: "bg-sodium shadow-[0_0_6px_rgba(198,137,34,0.5)]",
  err: "bg-signal-err shadow-[0_0_6px_rgba(196,74,54,0.5)]",
  idle: "bg-ink-faint",
};

export function StatusDot({ state, pulse, className }: StatusDotProps) {
  return (
    <span className={cn("relative inline-block h-1.5 w-1.5 rounded-full", colors[state], className)}>
      {pulse && state !== "idle" && (
        <span aria-hidden className={cn("absolute inset-0 animate-ping rounded-full opacity-60", colors[state])} />
      )}
    </span>
  );
}
