import { Play, SlidersHorizontal } from "lucide-react";

import type { WorkflowId } from "@/entities/workflow";
import type { WorkspaceId } from "@/entities/workspace";
import { cn } from "@/shared/lib/cn";

import { useWorkflowBuilderStore } from "../model/workflow-builder.store";
import { TestRunPanel } from "./TestRunPanel";
import { WorkflowInspector } from "./WorkflowInspector";

type Props = {
  workspaceId: WorkspaceId;
  workflowId: WorkflowId;
};

/**
 * Tabbed wrapper around the existing Inspector + the new Test Run panel.
 * Keeps the canvas alongside a single right column (no extra layout
 * gymnastics) while letting operators toggle modes without leaving the
 * workflow detail screen.
 */
export function WorkflowRightPanel({ workspaceId, workflowId }: Props) {
  const tab = useWorkflowBuilderStore((s) => s.rightPanelTab);
  const setTab = useWorkflowBuilderStore((s) => s.setRightPanelTab);

  return (
    <aside className="flex w-[360px] shrink-0 flex-col border-l border-canvas-rule bg-canvas-panel">
      <div className="flex border-b border-canvas-rule">
        <TabButton
          active={tab === "inspector"}
          onClick={() => setTab("inspector")}
          icon={<SlidersHorizontal size={12} strokeWidth={1.6} />}
        >
          Inspector
        </TabButton>
        <TabButton
          active={tab === "test_run"}
          onClick={() => setTab("test_run")}
          icon={<Play size={12} strokeWidth={1.6} />}
        >
          Test Run
        </TabButton>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden">
        {tab === "inspector" ? (
          <div className="h-full overflow-y-auto">
            <WorkflowInspector workspaceId={workspaceId} />
          </div>
        ) : (
          <TestRunPanel workspaceId={workspaceId} workflowId={workflowId} />
        )}
      </div>
    </aside>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "-mb-px flex flex-1 items-center justify-center gap-1.5 border-b-2 px-3 py-2 text-[11px] transition-colors",
        active
          ? "border-sodium text-ink"
          : "border-transparent text-ink-mute hover:text-ink",
      )}
    >
      {icon}
      {children}
    </button>
  );
}
