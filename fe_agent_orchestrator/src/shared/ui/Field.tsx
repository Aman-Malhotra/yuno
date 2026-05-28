import type { ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

type FieldProps = {
  label: ReactNode;
  hint?: ReactNode;
  error?: string;
  required?: boolean;
  children: ReactNode;
  className?: string;
};

export function Field({ label, hint, error, required, children, className }: FieldProps) {
  return (
    <label className={cn("flex flex-col gap-1.5", className)}>
      <span className="text-xs font-medium text-ink-dim">
        {label}
        {required && <span className="text-signal-err"> *</span>}
      </span>
      {children}
      {hint && !error && <span className="text-xs text-ink-mute">{hint}</span>}
      {error && <span className="text-xs text-signal-err">{error}</span>}
    </label>
  );
}
