import type { ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

export type MetricAccent = "neutral" | "sodium" | "ok" | "err";

type MetricCardProps = {
  label: string;
  value: ReactNode;
  sublabel?: ReactNode;
  trend?: ReactNode;
  accent?: MetricAccent;
  index?: number;
  className?: string;
};

const accentBar: Record<MetricAccent, string> = {
  neutral: "bg-canvas-ruleStrong",
  sodium: "bg-sodium shadow-[0_0_8px_rgba(198,137,34,0.35)]",
  ok: "bg-signal-ok",
  err: "bg-signal-err",
};

export function MetricCard({ label, value, sublabel, trend, accent = "neutral", index, className }: MetricCardProps) {
  return (
    <article
      className={cn(
        "group relative flex h-full flex-col justify-between bg-canvas-panel px-5 pb-4 pt-5",
        "border-r border-canvas-rule last:border-r-0",
        className,
      )}
    >
      <span aria-hidden className={cn("absolute left-0 top-0 h-px w-10", accentBar[accent])} />
      {index != null && (
        <span aria-hidden className="absolute right-3 top-2 font-mono text-[10px] tracking-eyebrow text-ink-faint">
          {String(index).padStart(2, "0")}
        </span>
      )}

      <header className="flex items-baseline justify-between">
        <span className="eyebrow">{label}</span>
        {trend && <span className="text-[10px] text-ink-mute">{trend}</span>}
      </header>

      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-[40px] font-thin tabular-nums leading-none text-ink">{value}</span>
      </div>

      {sublabel && <p className="mt-3 font-mono text-[11px] tracking-tight text-ink-mute">{sublabel}</p>}
    </article>
  );
}
