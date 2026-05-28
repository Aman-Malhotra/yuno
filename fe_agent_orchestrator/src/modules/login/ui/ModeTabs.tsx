import { cn } from "@/shared/lib/cn";
import type { AuthMode } from "../config/login.config";

type ModeTabsProps = {
  mode: AuthMode;
  onChange: (mode: AuthMode) => void;
};

const tabs: { value: AuthMode; label: string }[] = [
  { value: "signin", label: "Sign in" },
  { value: "signup", label: "Create account" },
];

export function ModeTabs({ mode, onChange }: ModeTabsProps) {
  return (
    <div
      role="tablist"
      aria-label="Authentication mode"
      className="inline-flex items-center gap-0.5 rounded-md border border-canvas-rule bg-canvas-inset p-0.5"
    >
      {tabs.map((t) => {
        const active = mode === t.value;
        return (
          <button
            key={t.value}
            role="tab"
            type="button"
            aria-selected={active}
            onClick={() => onChange(t.value)}
            className={cn(
              "relative h-7 rounded-[5px] px-3 text-[11px] font-medium transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sodium/40",
              active ? "bg-canvas-panel text-ink shadow-panel" : "text-ink-mute hover:text-ink-dim",
            )}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}
