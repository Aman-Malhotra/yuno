import { cn } from "@/shared/lib/cn";

type BrandProps = {
  className?: string;
  productLabel?: string;
};

/**
 * Yuno brand lockup: constellation mark + wordmark.
 *
 * The mark is the raw asset at `/logo.png` (sourced from the design file).
 * Vite serves files in `public/` from the site root, so this works in both
 * dev and prod builds. Use `YunoMark` directly when you want the icon-only
 * version (sidebar collapsed, favicon-adjacent contexts, etc).
 */
export function Brand({ className, productLabel = "Orchestrator" }: BrandProps) {
  return (
    <span className={cn("inline-flex select-none items-center gap-2", className)}>
      <YunoMark className="h-6 w-6 shrink-0" />
      <span className="text-sm font-medium tracking-tight text-ink">Yuno</span>
      <span className="text-sm font-light text-ink-dim">{productLabel}</span>
    </span>
  );
}

type MarkProps = {
  className?: string;
  alt?: string;
};

export function YunoMark({ className, alt = "Yuno" }: MarkProps) {
  return <img src="/logo.png" alt={alt} className={cn("object-contain", className)} draggable={false} />;
}
