---
title: Workflow Validation is Pure
impact: CRITICAL
impactDescription: Validation mixed with React means you can't unit-test it, run it server-side, or share it with the backend
tags: workflow-builder, validation, pure-functions
---

## Workflow Validation is Pure

`graph-validation.ts` is a set of pure functions. No React imports. No API calls. No side effects.

### Signature

```ts
// modules/workflow-builder/lib/graph-validation.ts
import type { WorkflowDraft, WorkflowNode, WorkflowEdge } from "@/entities/workflow";

export type WorkflowValidationError = {
  level: "error" | "warning";
  scope: "graph" | "node" | "edge";
  nodeId?: string;
  edgeId?: string;
  code: WorkflowValidationCode;
  message: string;
};

export type WorkflowValidationResult = {
  ok: boolean;
  errors: WorkflowValidationError[];
};

export function validateWorkflow(draft: WorkflowDraft): WorkflowValidationResult {
  const errors: WorkflowValidationError[] = [];

  errors.push(...checkExactlyOneStart(draft));
  errors.push(...checkAtLeastOneEnd(draft));
  errors.push(...checkNoOrphanNodes(draft));
  errors.push(...checkNoIncomingToStart(draft));
  errors.push(...checkNoOutgoingFromEnd(draft));
  errors.push(...checkAgentNodesHaveAgentId(draft));
  errors.push(...checkToolNodesHaveToolId(draft));
  errors.push(...checkConditionBranches(draft));
  errors.push(...checkNoUnconfiguredCycles(draft));
  errors.push(...checkNodeConfigSchemas(draft));

  return { ok: errors.every((e) => e.level !== "error"), errors };
}
```

### Required checks for Yuno

| Check                              | Code                          | Level    |
|------------------------------------|-------------------------------|----------|
| Exactly one `start` node           | `MISSING_START` / `MULTIPLE_START` | error |
| At least one `end` node            | `MISSING_END`                 | error    |
| Agent node has `agentId`           | `AGENT_NODE_MISSING_AGENT`    | error    |
| Tool node has `toolId`             | `TOOL_NODE_MISSING_TOOL`      | error    |
| Condition node has both branches   | `CONDITION_MISSING_BRANCH`    | error    |
| No edges into start                | `EDGE_INTO_START`             | error    |
| No edges out of end                | `EDGE_OUT_OF_END`             | error    |
| No orphan nodes                    | `ORPHAN_NODE`                 | warning  |
| No cycles unless `feedback` edge   | `UNCONTROLLED_CYCLE`          | warning  |
| Each node config matches its Zod schema | `INVALID_NODE_CONFIG`    | error    |

Yuno requires feedback loops as a feature, so cycles aren't outright banned — but a cycle must include an edge explicitly marked as a feedback edge (and ideally a stop condition).

### Wire to UI without coupling

```ts
// modules/workflow-builder/ui/WorkflowToolbar.tsx
const result = validateWorkflow(currentDraft);
const canPublish = result.ok;
```

```ts
// surface per-node errors as overlays
const errorsByNode = groupBy(result.errors, (e) => e.nodeId);
```

### Bad — mixing React in validation

```ts
// ❌ Can't run server-side, can't unit test
export function validateWorkflow(draft) {
  const { toast } = useToast();
  toast.error("..."); // side effect inside validation
}
```

### Good — surface errors at the call site

```ts
// ✅ Validation returns data; UI decides how to render
const result = validateWorkflow(draft);
if (!result.ok) toast.error(`${result.errors.length} issues`);
```

See: [[workflow-builder-canvas]], [[workflow-builder-node-registry]]
