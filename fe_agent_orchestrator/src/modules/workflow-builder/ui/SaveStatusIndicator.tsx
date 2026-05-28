import { Check, CircleAlert, Loader2, Pencil } from "lucide-react";

import { cn } from "@/shared/lib/cn";

import { useWorkflowBuilderStore } from "../model/workflow-builder.store";

export function SaveStatusIndicator({ readOnly = false }: { readOnly?: boolean }) {
  const status = useWorkflowBuilderStore((s) => s.saveStatus);
  const lastSavedAt = useWorkflowBuilderStore((s) => s.lastSavedAt);
  const error = useWorkflowBuilderStore((s) => s.saveError);

  if (readOnly) {
    return <span className="text-[11px] uppercase tracking-eyebrow text-ink-mute">read-only</span>;
  }

  const { icon: Icon, label, tone } = render(status, lastSavedAt, error);

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-[11px] uppercase tracking-eyebrow",
        tone === "ok" && "text-signal-ok",
        tone === "err" && "text-signal-err",
        tone === "info" && "text-ink-mute",
      )}
      role="status"
    >
      <Icon size={12} strokeWidth={1.8} className={status === "saving" ? "animate-spin" : ""} />
      {label}
    </span>
  );
}

function render(
  status: "idle" | "dirty" | "saving" | "saved" | "error",
  lastSavedAt: string | null,
  error: string | null,
): { icon: typeof Check; label: string; tone: "ok" | "err" | "info" } {
  switch (status) {
    case "saving":
      return { icon: Loader2, label: "saving…", tone: "info" };
    case "dirty":
      return { icon: Pencil, label: "unsaved changes", tone: "info" };
    case "saved":
      return { icon: Check, label: formatSaved(lastSavedAt), tone: "ok" };
    case "error":
      return { icon: CircleAlert, label: error ?? "save failed", tone: "err" };
    case "idle":
    default:
      return { icon: Check, label: "up to date", tone: "info" };
  }
}

function formatSaved(iso: string | null): string {
  if (!iso) return "saved";
  try {
    const t = new Date(iso);
    return `saved ${t.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}`;
  } catch {
    return "saved";
  }
}
