import { X } from "lucide-react";

import { CreateWorkspaceForm } from "./CreateWorkspaceForm";
import type { WorkspaceSummary } from "@/entities/workspace";

type Props = {
  onSuccess: (ws: WorkspaceSummary) => void;
  onCancel: () => void;
};

/**
 * Inline form variant of CreateWorkspaceTile — sits in the same grid slot,
 * keeps the 33% column width, just renders the form instead of the prompt.
 */
export function CreateWorkspaceCard({ onSuccess, onCancel }: Props) {
  return (
    <div className="flex flex-col gap-3 rounded-md border border-sodium/60 bg-canvas-panel p-4 shadow-elev">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span aria-hidden className="h-px w-6 bg-sodium" />
          <span className="eyebrow">New workspace</span>
        </div>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-sm p-1 text-ink-mute transition-colors hover:bg-canvas-inset hover:text-ink"
          aria-label="Cancel"
        >
          <X size={14} strokeWidth={1.8} />
        </button>
      </header>
      <CreateWorkspaceForm onSuccess={onSuccess} onCancel={onCancel} />
    </div>
  );
}
