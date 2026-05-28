import type { ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

type SectionHeaderProps = {
  eyebrow?: string;
  title: ReactNode;
  meta?: ReactNode;
  right?: ReactNode;
  className?: string;
};

export function SectionHeader({ eyebrow, title, meta, right, className }: SectionHeaderProps) {
  return (
    <header className={cn("flex items-end justify-between gap-4", className)}>
      <div className="flex flex-col gap-1.5">
        {eyebrow && (
          <div className="flex items-center gap-2">
            <span aria-hidden className="h-px w-6 bg-sodium" />
            <span className="eyebrow">{eyebrow}</span>
          </div>
        )}
        <h2 className="text-[22px] font-light leading-none text-ink">{title}</h2>
        {meta && <p className="text-[11px] text-ink-mute">{meta}</p>}
      </div>
      {right && <div className="flex items-center gap-2">{right}</div>}
    </header>
  );
}
