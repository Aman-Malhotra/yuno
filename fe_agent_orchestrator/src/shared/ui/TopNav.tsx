import type { ComponentType, ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { cn } from "@/shared/lib/cn";
import { Brand } from "./Brand";

type IconProps = { className?: string; size?: number; strokeWidth?: number };
export type IconComponent = ComponentType<IconProps>;

export type TopNavTab = {
  to: string;
  label: string;
  icon: IconComponent;
};

type TopNavProps = {
  tabs: TopNavTab[];
  right?: ReactNode;
  className?: string;
};

export function TopNav({ tabs, right, className }: TopNavProps) {
  return (
    <header
      className={cn(
        "sticky top-0 z-20 grid h-14 items-center gap-6 border-b border-canvas-rule",
        "bg-canvas-panel/90 px-6 backdrop-blur",
        "grid-cols-[auto_1fr_auto]",
        className,
      )}
    >
      <Link to="/" className="inline-flex items-center">
        <Brand />
      </Link>

      <nav className="flex items-center justify-center gap-1">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <Link
              key={tab.to}
              to={tab.to}
              className="group relative inline-flex items-center gap-2 px-3 py-2 text-[12px] text-ink-dim transition-colors hover:text-ink"
              activeProps={{ className: "text-ink" }}
            >
              {({ isActive }) => (
                <>
                  <Icon
                    size={14}
                    strokeWidth={1.5}
                    className={cn(
                      "transition-colors",
                      isActive ? "text-sodium" : "text-ink-mute group-hover:text-ink-dim",
                    )}
                  />
                  <span>{tab.label}</span>
                  <span
                    aria-hidden
                    className={cn(
                      "pointer-events-none absolute -bottom-px left-3 right-3 h-px",
                      isActive ? "bg-sodium shadow-[0_0_8px_rgba(198,137,34,0.55)]" : "bg-transparent",
                    )}
                  />
                </>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="flex items-center gap-3">{right}</div>
    </header>
  );
}
