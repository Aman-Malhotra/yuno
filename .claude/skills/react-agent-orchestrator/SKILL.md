---
name: react-agent-orchestrator
description: React + TypeScript architecture skill for building the Yuno AI agent orchestration platform UI. Covers stack, feature-based module structure, three-way state management split (server/local/form), React Flow workflow builder, agent CRUD, LLM provider boundaries, and realtime run monitoring. TRIGGER when writing, reviewing, or scaffolding any frontend code for the Yuno agent orchestration UI (agents, workflows, runs, providers, channels, playground).
license: MIT
metadata:
  author: Aman Malhotra
  version: "1.0.0"
  project: yuno-ai-agent-orchestrator
---

# React Agent Orchestrator

Frontend architecture rules for the Yuno AI Engineer Challenge — an agent orchestration platform where users create agents, configure tools/memory/channels, connect them in visual workflows, and monitor live runs that talk to WhatsApp/Telegram/Slack.

## When to Apply

Reference these rules when:

- Scaffolding the React frontend
- Adding any new agent/workflow/run/provider/channel feature
- Reviewing component placement (which folder?)
- Choosing state location (server / local / form)
- Adding LLM provider config UI
- Wiring realtime run logs / inter-agent messages

## Yuno Challenge Mapping

| Challenge requirement              | Rule(s)                                                |
|------------------------------------|--------------------------------------------------------|
| Agent CRUD                         | `agent-creation-stepper`, `agent-editor-layout`        |
| Visual workflow builder            | `workflow-builder-canvas`, `workflow-builder-node-registry`, `workflow-builder-validation` |
| Live monitoring (logs, messages)   | `realtime-run-events`                                  |
| Channel integration (WA/TG/Slack)  | `channel-integration-ui`                               |
| Token/cost tracking                | `realtime-run-events`                                  |
| Web UI for managing everything     | `arch-feature-modules`, `stack-choices`                |
| Persisted message history          | `state-server-tanstack-query`, `realtime-run-events`   |

## Rule Categories by Priority

| Priority | Category               | Impact   | Prefix       |
|----------|------------------------|----------|--------------|
| 1        | Stack                  | CRITICAL | `stack-`     |
| 2        | Architecture           | CRITICAL | `arch-`      |
| 3        | State management       | CRITICAL | `state-`     |
| 4        | Workflow builder       | CRITICAL | `workflow-`  |
| 5        | Agent UI               | HIGH     | `agent-`     |
| 6        | LLM boundaries         | HIGH     | `llm-`       |
| 7        | Realtime + channels    | HIGH     | `realtime-`, `channel-` |
| 8        | API layer              | MEDIUM   | `api-`       |
| 9        | TypeScript             | MEDIUM   | `ts-`        |
| 10       | Naming                 | LOW      | `naming-`    |

## Quick Reference

### 1. Stack (CRITICAL)

- `stack-choices` — React + TS + Vite, React Flow, TanStack Query, Zustand, RHF+Zod, Tailwind+shadcn, Monaco, SSE/WS

### 2. Architecture (CRITICAL)

- `arch-feature-modules` — entities/features/modules/shared/app/pages layout
- `arch-dependency-direction` — app → pages → modules → features → entities → shared; never import upward
- `arch-module-boundaries` — cross-module imports only via `index.ts`

### 3. State management (CRITICAL)

- `state-server-tanstack-query` — all backend data lives in TanStack Query, never duplicated in Zustand
- `state-local-zustand` — UI-only state (selection, panels, canvas mode, drafts)
- `state-form-rhf-zod` — every form is React Hook Form + Zod resolver

### 4. Workflow builder (CRITICAL — product core)

- `workflow-builder-canvas` — React Flow as the canvas, client-side only
- `workflow-builder-node-registry` — node types registered once, components/schemas co-located
- `workflow-builder-validation` — pure functions, no React, run before publish

### 5. Agent UI (HIGH)

- `agent-creation-stepper` — basics → LLM → prompt → tools → memory → review
- `agent-editor-layout` — three-column: sections / editor / test console
- `agent-feature-reuse` — share `features/configure-llm`, `features/configure-tool`, `features/manage-memory` between create and edit

### 6. LLM boundaries (HIGH)

- `llm-frontend-never-calls-providers` — no OpenAI/Anthropic/Gemini/Groq SDK in browser, ever
- `llm-backend-interface` — single `LlmProvider` interface backend-side; one impl per provider

### 7. Realtime + channels (HIGH)

- `realtime-run-events` — SSE/WS stream for run events, logs, inter-agent messages, token usage
- `channel-integration-ui` — channel config UI is frontend; webhook handling stays backend

### 8. API layer (MEDIUM)

- `api-http-client` — typed fetch wrapper + Zod response parsing
- `api-query-keys` — one central key factory per entity; invalidate via key prefixes

### 9. TypeScript (MEDIUM)

- `ts-strict` — strict mode + `noUncheckedIndexedAccess` + branded ids for `AgentId`, `WorkflowId`, `RunId`, `NodeId`

### 10. Naming (LOW)

- `naming-conventions` — file/component/hook/store/schema naming

## How to Use

Each rule file contains:

- One-line statement of the rule
- Why it matters in the Yuno context
- Bad / good code examples (TypeScript)
- Cross-references to related rules

Read a rule:

```
rules/arch-feature-modules.md
rules/state-server-tanstack-query.md
rules/workflow-builder-node-registry.md
```

## Target Folder Structure

The architecture rules collectively produce this layout. Use it as the starting skeleton:

```txt
src/
  app/
    main.tsx
    App.tsx
    providers/         # QueryProvider, ThemeProvider, AuthProvider
    router/
    config/            # env, feature flags
  shared/
    api/               # http-client, api-error, query-keys
    ui/                # shadcn-based primitives
    lib/               # cn, date, ids, debounce
    types/             # Brand, Pagination, Result
  entities/
    agent/             # model + api + small UI bits (badges, cards)
    workflow/
    llm-provider/
    tool/
    memory/
    run/
    channel/
    user/
    project/
  features/            # one user-facing action per folder
    create-agent/
    edit-agent/
    configure-llm/
    configure-tool/
    manage-memory/
    test-agent/
    publish-workflow/
    run-workflow/
    inspect-run/
    connect-channel/
  modules/             # full product areas
    agent-creation/
    agent-editor/
    workflow-builder/
    workflow-runner/
    llm-playground/
    channel-registry/
    run-monitor/
  pages/
    agents/
    workflows/
    runs/
    providers/
    channels/
    settings/
```
