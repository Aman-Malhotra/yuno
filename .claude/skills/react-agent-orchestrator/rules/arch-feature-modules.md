---
title: Feature/Module-Based Architecture
impact: CRITICAL
impactDescription: Keeps a multi-area app (agents + workflows + runs + providers + channels) navigable as it grows
tags: architecture, folder-structure, layering
---

## Feature/Module-Based Architecture

Organize by **what the user does**, not by technical layer. Five layers, each with a clear role.

| Layer       | Contains                                           | Example for Yuno                                   |
|-------------|----------------------------------------------------|----------------------------------------------------|
| `app/`      | Bootstrapping: providers, router, query client     | `AppProviders.tsx`, `routes.tsx`                   |
| `pages/`    | Route-level screens, mostly compose a module       | `pages/workflows/[id].tsx` → `<WorkflowBuilderPage />` |
| `modules/`  | Full product areas with their own layout/state     | `agent-editor/`, `workflow-builder/`, `run-monitor/` |
| `features/` | One user action, reused across modules             | `create-agent/`, `configure-llm/`, `test-agent/`   |
| `entities/` | Business objects: types, schemas, API, small UI    | `agent/`, `workflow/`, `run/`, `llm-provider/`     |
| `shared/`   | Reusable UI, http client, utilities, types         | `shared/ui/Button.tsx`, `shared/api/http-client.ts` |

### Bad: layer-first folders

```txt
src/
  components/     ← unrelated stuff piles up
  hooks/          ← random hooks, no boundary
  services/       ← god-folder
  utils/
  pages/
```

You end up grepping by name instead of navigating by feature.

### Good: feature/module-first

```txt
src/
  app/
  shared/
  entities/
    agent/
    workflow/
    run/
    llm-provider/
    tool/
    channel/
  features/
    create-agent/
    configure-llm/
    test-agent/
    connect-channel/
  modules/
    agent-creation/
    agent-editor/
    workflow-builder/
    workflow-runner/
    run-monitor/
    llm-playground/
  pages/
    agents/
    workflows/
    runs/
    providers/
    channels/
```

### Rules of thumb

- A new screen → add a `pages/*` file that mounts an existing module
- A new product area → new `modules/*` folder
- A new reusable action → new `features/*` folder
- A new business object → new `entities/*` folder
- A new primitive/util → goes in `shared/*`

See: [[arch-dependency-direction]], [[arch-module-boundaries]]
