---
title: Dependency Direction
impact: CRITICAL
impactDescription: One upward import creates a cycle; cycles make the workflow builder unbuildable in isolation
tags: architecture, layering, imports
---

## Dependency Direction

Imports must flow **downward only**:

```txt
app  →  pages  →  modules  →  features  →  entities  →  shared
```

### Allowed

```ts
// modules/workflow-builder/ui/WorkflowCanvas.tsx
import { AgentCard } from "@/entities/agent";              // module → entity ✅
import { ConfigureLlmForm } from "@/features/configure-llm"; // module → feature ✅
import { Button } from "@/shared/ui/Button";               // any → shared ✅

// features/edit-agent/ui/EditAgentForm.tsx
import { agentSchema } from "@/entities/agent";            // feature → entity ✅
```

### Forbidden

```ts
// entities/agent/ui/AgentCard.tsx
import { WorkflowBuilderPage } from "@/modules/workflow-builder"; // entity → module ❌

// shared/ui/Button.tsx
import { useCreateAgent } from "@/features/create-agent";  // shared → feature ❌

// features/edit-agent/ui/EditAgentForm.tsx
import { AgentEditorPage } from "@/modules/agent-editor";  // feature → module ❌
```

### Enforce with `eslint-plugin-boundaries`

```js
// .eslintrc.cjs
module.exports = {
  plugins: ["boundaries"],
  settings: {
    "boundaries/elements": [
      { type: "app",      pattern: "src/app/**" },
      { type: "pages",    pattern: "src/pages/**" },
      { type: "modules",  pattern: "src/modules/**" },
      { type: "features", pattern: "src/features/**" },
      { type: "entities", pattern: "src/entities/**" },
      { type: "shared",   pattern: "src/shared/**" }
    ]
  },
  rules: {
    "boundaries/element-types": ["error", {
      default: "disallow",
      rules: [
        { from: "app",      allow: ["pages", "modules", "features", "entities", "shared"] },
        { from: "pages",    allow: ["modules", "features", "entities", "shared"] },
        { from: "modules",  allow: ["features", "entities", "shared"] },
        { from: "features", allow: ["entities", "shared"] },
        { from: "entities", allow: ["shared"] },
        { from: "shared",   allow: ["shared"] }
      ]
    }]
  }
};
```

### Decision rule before adding an import

Ask: "Is the target file in a layer below me?" If no, restructure — usually the shared piece belongs in `shared/` or as an `entity`.

See: [[arch-feature-modules]], [[arch-module-boundaries]]
