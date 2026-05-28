import type { ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

type ChipProps = {
  children: ReactNode;
  icon?: ReactNode;
  tone?: "default" | "ok" | "warn" | "err" | "accent";
  className?: string;
};

const toneClasses: Record<NonNullable<ChipProps["tone"]>, string> = {
  default: "border-canvas-ruleStrong bg-canvas-inset text-ink-dim",
  ok: "border-signal-ok/40 bg-signal-ok/10 text-signal-ok",
  warn: "border-sodium/50 bg-sodium-tint text-sodium",
  err: "border-signal-err/50 bg-signal-err/10 text-signal-err",
  accent: "border-sodium/50 bg-sodium-tint text-sodium",
};

export function Chip({ children, icon, tone = "default", className }: ChipProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5",
        "text-[10px] uppercase tracking-eyebrow",
        toneClasses[tone],
        className,
      )}
    >
      {icon && <span className="text-[10px]">{icon}</span>}
      {children}
    </span>
  );
}
