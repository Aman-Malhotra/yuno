import { useEffect, useRef } from "react";

import { useUpdateWorkflowGraph, type WorkflowId } from "@/entities/workflow";
import type { WorkspaceId } from "@/entities/workspace";

import { useWorkflowBuilderStore } from "../model/workflow-builder.store";

const DEFAULT_DEBOUNCE_MS = 600;

/**
 * Debounced autosave loop for the React Flow canvas.
 *
 * Watches the store's `graphRevision` counter — every node/edge mutation
 * bumps it; this hook waits `debounceMs` after the *last* bump, then PATCHes
 * `/workflows/{id}/graph`. While saving, further edits land in the store
 * and re-arm the timer, so the request count stays bounded even during a
 * heavy editing burst.
 *
 * The mounting page is responsible for ensuring the workflow exists
 * before this hook activates (i.e. on the "new workflow" page, create
 * first, then mount the builder with the resulting `workflowId`).
 */
export function useGraphAutosave(
  workspaceId: WorkspaceId,
  workflowId: WorkflowId,
  debounceMs: number = DEFAULT_DEBOUNCE_MS,
): void {
  const graphRevision = useWorkflowBuilderStore((s) => s.graphRevision);
  const saveStatus = useWorkflowBuilderStore((s) => s.saveStatus);
  const toGraph = useWorkflowBuilderStore((s) => s.toWorkflowGraph);
  const markSaving = useWorkflowBuilderStore((s) => s.markSaving);
  const markSaved = useWorkflowBuilderStore((s) => s.markSaved);
  const markError = useWorkflowBuilderStore((s) => s.markError);

  const mutation = useUpdateWorkflowGraph(workspaceId, workflowId);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    // `idle` = freshly loaded baseline; skip the first tick after setGraph.
    if (saveStatus !== "dirty") return;

    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      const graph = toGraph();
      markSaving();
      mutation.mutate(graph, {
        onSuccess: () => markSaved(),
        onError: (err: unknown) => {
          markError(err instanceof Error ? err.message : "Save failed");
        },
      });
    }, debounceMs);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
    // Intentionally exclude `mutation` from deps — it's a stable mutation
    // object whose identity is fine as a closure capture; including it
    // would re-arm the timer on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graphRevision, debounceMs, saveStatus]);
}
