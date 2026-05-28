import { Plus } from "lucide-react";

type Props = {
  onClick: () => void;
};

/**
 * Always-first grid item on the dashboard. Visually a dashed-border card
 * with a "+" hint; clicking it swaps the card content for the inline
 * create form (see DashboardPage).
 */
export function CreateWorkspaceTile({ onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex min-h-[156px] flex-col items-center justify-center gap-3 rounded-md border border-dashed border-canvas-ruleStrong bg-canvas-panel/40 p-4 transition-colors hover:border-sodium hover:bg-canvas-panel focus-visible:border-sodium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sodium/30"
    >
      <span
        aria-hidden
        className="flex h-9 w-9 items-center justify-center rounded-md border border-canvas-ruleStrong bg-canvas-inset text-ink-mute transition-colors group-hover:border-sodium group-hover:text-sodium"
      >
        <Plus size={16} strokeWidth={1.8} />
      </span>
      <span className="text-[12px] font-medium text-ink">New workspace</span>
      <span className="text-[10px] uppercase tracking-eyebrow text-ink-mute">click to create</span>
    </button>
  );
}
