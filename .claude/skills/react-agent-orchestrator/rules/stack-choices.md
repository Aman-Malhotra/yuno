---
title: Stack Choices
impact: CRITICAL
impactDescription: Wrong stack picks compound — switching React Flow, query lib, or form lib mid-build is days of churn
tags: stack, vite, react-flow, tanstack-query, zustand, tailwind, shadcn
---

## Stack Choices

Use exactly this stack. Each pick is justified by a Yuno requirement.

| Concern              | Choice                          | Why for Yuno                                                 |
|----------------------|---------------------------------|--------------------------------------------------------------|
| Framework            | React + TypeScript              | Required by spec; ecosystem fits everything below            |
| Build                | **Vite**                        | App-only product, no SSR needed; fastest dev loop            |
| Routing              | TanStack Router or React Router | Pick one — both fine                                         |
| Canvas               | **React Flow / xyflow**         | Built for node-based editors; workflow builder is the core   |
| Server state         | **TanStack Query**              | Fetch/cache/invalidate agents, workflows, runs               |
| Local UI state       | **Zustand**                     | Tiny hook store for selection, panels, canvas mode           |
| Forms                | **React Hook Form + Zod**       | Agent/workflow/LLM config forms with schema-driven validation |
| Styling              | Tailwind + shadcn/ui + Radix    | Fast to build, accessible primitives                         |
| Tables               | TanStack Table                  | Runs list, message history                                   |
| Code editor          | Monaco                          | System prompt editor, JSON tool schema editor                |
| Realtime             | SSE (preferred) or WebSocket    | Run events, inter-agent messages, token usage stream         |
| Validation           | Zod                             | Shared between forms and API response parsing                |
| HTTP                 | Native `fetch` wrapper          | No need for Axios features here                              |
| Testing              | Vitest + RTL + Playwright       | Vitest pairs with Vite; Playwright for the demo flow         |
| Lint/format          | ESLint + Prettier + TS strict   |                                                              |

### Do not pick

- **Next.js** — there's no SSR/SEO requirement; the workflow canvas is fully interactive and would all end up `"use client"` anyway
- **Redux / MobX / Recoil** — Zustand + TanStack Query covers everything we need
- **Axios** — adds a dependency for features we don't use
- **Formik** — RHF is faster and integrates with Zod cleanly
- **Material UI / Ant Design** — clashes with the custom canvas/inspector visual style; shadcn lets you own the components
- **InversifyJS or other DI containers** — overkill on the frontend; constructor params + React Context are enough

### Minimum `package.json` core

```json
{
  "dependencies": {
    "react": "^18",
    "react-dom": "^18",
    "@tanstack/react-query": "^5",
    "zustand": "^4",
    "react-hook-form": "^7",
    "@hookform/resolvers": "^3",
    "zod": "^3",
    "reactflow": "^11",
    "@monaco-editor/react": "^4",
    "tailwindcss": "^3",
    "clsx": "^2",
    "tailwind-merge": "^2"
  }
}
```

Add shadcn components via its CLI as you need them — do not pull a UI kit wholesale.

See: [[arch-feature-modules]], [[state-server-tanstack-query]], [[workflow-builder-canvas]]
