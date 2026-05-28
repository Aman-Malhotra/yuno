# fe_agent_orchestrator

Frontend for the Yuno AI Agent Orchestration Platform.
Built per the project skill at `../.claude/skills/react-agent-orchestrator/`.

## Stack

- **React + TypeScript + Vite** — fast dev loop, no SSR
- **TanStack Query** — all server state (agents, workflows, runs)
- **TanStack Router** — typed file-less router
- **Zustand** — local UI state (selection, canvas mode, panels)
- **React Hook Form + Zod** — every form
- **React Flow / xyflow** — workflow builder canvas
- **Tailwind CSS** — styling
- **Native `fetch` + Zod** — HTTP client with schema-validated responses
- **EventSource (SSE)** — realtime run events

No Axios, no Redux, no provider SDKs in the browser (LLM calls go through the backend — see the skill's `llm-frontend-never-calls-providers` rule).

## Quick start

```sh
make install      # npm install
make dev          # vite dev server on :3000
```

Open <http://localhost:3000>.

The dev server proxies `/api/*` to `http://localhost:8000` (configured in `vite.config.ts`). Without a backend running, list queries will fail — the agents page renders an error state, which is fine while iterating on the UI.

## Make targets

| Target              | What it does                                                    |
| ------------------- | --------------------------------------------------------------- |
| `make install`      | `npm install`                                                   |
| `make dev`          | Vite dev server on `:3000`                                      |
| `make build`        | Type-check + production bundle to `dist/`                       |
| `make run`          | Build then serve the bundle on `:3000` (host `0.0.0.0`)         |
| `make preview`      | Serve an existing `dist/` bundle on `:3000`                     |
| `make format`       | Prettier write (120 col)                                        |
| `make format-check` | Prettier check                                                  |
| `make lint`         | ESLint                                                          |
| `make lint-fix`     | ESLint with `--fix`                                             |
| `make typecheck`    | `tsc -b --noEmit`                                               |
| `make analyze`      | typecheck + lint + format-check, full log in `logs/analyze.log` |
| `make clean`        | Remove `dist/`, `logs/`, `.vite`                                |
| `make docker-build` | Build the Docker image (`yuno/fe_agent_orchestrator:local`)     |
| `make docker-run`   | Run container, map host `:3000` → container `:3000`             |
| `make docker-stop`  | Stop the container                                              |
| `make docker-logs`  | Tail container logs                                             |

Override ports: `make dev PORT=4000`, `make docker-run DOCKER_PORT=8080`.

## Docker

Multi-stage build: `node:20-alpine` compiles, `nginx:1.27-alpine` serves on port 3000. SPA fallback to `index.html`, gzip on, hashed assets cached for 1 year.

```sh
make docker-build
make docker-run        # http://localhost:3000
make docker-logs       # tail
make docker-stop
```

The image only contains the static build — no Node runtime in production. Calls to `/api/*` must be routed to the backend by your reverse proxy / ingress at deploy time.

## Project layout

```
src/
  app/              providers, router, env config
  shared/           UI primitives, http client, lib, types
  entities/         agent, workflow, run (types + api + small UI)
  features/         user actions (create-agent, …)
  modules/          full product areas (workflow-builder, …)
  pages/            route-level screens (agents, workflows)
```

Architecture rules and rationale live in the skill at
`../.claude/skills/react-agent-orchestrator/`.

The short version:

- Imports flow downward only: `app → pages → modules → features → entities → shared`. Enforced by ESLint `no-restricted-imports`.
- Server data lives in TanStack Query, never duplicated into Zustand.
- All forms use React Hook Form + Zod.
- The workflow canvas is React Flow; node types live in a single registry (`src/modules/workflow-builder/model/node-registry.ts`).
- Graph validation is pure (`src/modules/workflow-builder/lib/graph-validation.ts`).
- LLM provider SDKs never ship to the browser — the frontend talks to our backend, which talks to providers.

## Formatting

Prettier with `printWidth: 120` (`.prettierrc.json`). ESLint also warns on lines > 120.

## Backend URL configuration (single source)

The backend base URL is **only configured in one place**: `src/app/config/env.ts`. Everything else builds on top of it.

- **Runtime URL** — `env.API_BASE_URL`, defaults to `/api`. Override per environment with `VITE_API_BASE_URL`.
- **Dev proxy** — Vite proxies `/api/*` to `http://localhost:3001` (the backend port for local dev). Override with `VITE_BACKEND_DEV_TARGET=http://localhost:9000 make dev`.

### API service classes

Each entity exposes its API through a service class extending the shared `ApiService` base (`src/shared/api/api-service.ts`). The base owns transport (`_get` / `_post` / `_patch` / `_put` / `_delete`); subclasses declare a resource path and CRUD verbs.

```ts
// src/entities/agent/api/agent.service.ts
class AgentService extends ApiService {
  constructor() {
    super("/agents"); // resource path, appended to env.API_BASE_URL
  }

  list = (f: AgentFilters = {}) => this._get(this.toQuery(f), agentListSchema);
  getById = (id: AgentId) => this._get(`/${id}`, agentSchema);
  create = (input: CreateAgentInput) => this._post("", input, agentSchema);
  update = (id: AgentId, input: Partial<CreateAgentInput>) => this._patch(`/${id}`, input, agentSchema);
  delete = (id: AgentId) => this._delete(`/${id}`, z.void());
}

export const agentApi = new AgentService();
```

Adding a new resource:

1. Make `src/entities/<thing>/api/<thing>.service.ts`.
2. Extend `ApiService` with the resource path.
3. Implement methods using `_get` / `_post` / etc. + a Zod response schema.
4. Export a singleton: `export const thingApi = new ThingService();`
5. Use it via TanStack Query hooks in `<thing>.queries.ts` / `<thing>.mutations.ts`.

No file ever hard-codes `http://localhost:3001` or hits `fetch` directly outside `httpRequest` — every HTTP path is built from the single base URL.

## Backend contract (what this UI expects)

- `GET    /api/agents` → `Agent[]`
- `GET    /api/agents/:id` → `Agent`
- `POST   /api/agents` → `Agent`
- `PATCH  /api/agents/:id` → `Agent`
- `DELETE /api/agents/:id` → `204`
- `GET    /api/runs/:id/events` → SSE stream of `RunEvent` (see `src/entities/run/model/run-event.types.ts`)

Schemas are defined with Zod and validated at the boundary — a backend response that doesn't match will throw at the call site rather than corrupting the UI.
