import { Check } from "lucide-react";
import { Brand } from "@/shared/ui";
import { loginCopy } from "../config/login.config";

export function AuthBranding() {
  return (
    <aside className="relative flex h-full flex-col justify-between overflow-hidden border-r border-canvas-rule bg-canvas-panel px-10 py-10">
      {/* faint registration ticks down the left edge */}
      <div
        aria-hidden
        className="pointer-events-none absolute left-0 top-0 flex h-full w-2 flex-col justify-between py-12"
      >
        {Array.from({ length: 12 }).map((_, i) => (
          <span key={i} className="h-px w-1.5 bg-canvas-ruleStrong" />
        ))}
      </div>

      <header className="flex flex-col gap-6">
        <Brand />
        <div className="flex items-center gap-2">
          <span aria-hidden className="h-px w-6 bg-sodium" />
          <span className="eyebrow">{loginCopy.productMarker}</span>
        </div>
        <h1 className="max-w-[18ch] text-[34px] font-light leading-[1.1] tracking-tight text-ink">
          {loginCopy.productTagline}
        </h1>
      </header>

      <ul className="flex flex-col gap-3">
        {loginCopy.bullets.map((b) => (
          <li key={b} className="flex items-start gap-2.5 text-[12px] text-ink-dim">
            <span
              aria-hidden
              className="mt-0.5 flex h-4 w-4 items-center justify-center rounded-[2px] border border-sodium/40 bg-sodium-tint"
            >
              <Check size={10} strokeWidth={2.4} className="text-sodium" />
            </span>
            <span>{b}</span>
          </li>
        ))}
      </ul>

      <footer className="flex items-center justify-between font-mono text-[10px] uppercase tracking-eyebrow text-ink-mute">
        <span>{loginCopy.footnote}</span>
        <span>v0.1 · trial build</span>
      </footer>
    </aside>
  );
}
