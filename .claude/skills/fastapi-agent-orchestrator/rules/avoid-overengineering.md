---
title: Avoid Overengineering
impact: MEDIUM
impactDescription: The grading rubric values "working end-to-end demo" (40%) far more than internal sophistication; gold-plating loses points
tags: discipline, scope, tradeoffs
---

## Avoid Overengineering

The Yuno challenge is graded:

- Working end-to-end demo — **40%**
- Architecture and code quality — **30%**
- UI/UX and configurability — **20%**
- Documentation — **10%**

A working demo that runs in one command beats a partly-implemented "production-grade" backend every time.

### Hard "no" list for this assignment

```txt
❌ Microservices (multiple deployable services)
❌ Kafka (Redis pub/sub covers it)
❌ Kubernetes / Helm
❌ A custom auth framework — JWT + pwdlib only
❌ A custom DI container (use FastAPI Depends)
❌ Stubbing all 4 LLM providers without finishing one fully
❌ WhatsApp Business if you don't already have a sandbox set up
❌ OpenTelemetry / Jaeger — custom runtime events already cover what the spec wants
❌ A second database (Mongo, ClickHouse) "for events" — Postgres JSONB is enough
❌ Workflow execution mocked in the UI (the spec explicitly forbids this)
❌ Logs only in memory — must be persisted (the spec explicitly requires this)
❌ Calling LLM APIs from the React frontend
```

### Soft "no" — defer unless time allows

```txt
~ A full streaming LLM pipeline end to end (start with non-streaming `complete`)
~ Multi-tenant workspaces (single-user with `user_id` ownership is enough)
~ Vector memory (sliding window of last N messages covers `memory_config` for demo)
~ Cron-scheduled agents (the schedule field can exist in JSONB without an active scheduler)
~ Cost tracking in USD (tokens are enough; convert in the UI)
~ Admin role + admin UI (the role field can exist; admin endpoints can be empty)
```

### "Yes" list — the demo must show these

```txt
✅ Auth (register + login)
✅ Agent CRUD (with at least: name, role, system prompt, model, tools, channel)
✅ Workflow CRUD + validation + 2 templates
✅ A workflow that runs 2+ agents handing off to each other
✅ Real LLM call (at least one provider fully working)
✅ Real tool execution (at least 2 tools)
✅ Telegram conversation: human DMs the bot → agent replies via the runtime
✅ Live monitoring: WebSocket stream of run events visible in the UI
✅ Persisted message history visible in the UI
✅ One-command local setup (docker compose up --build)
✅ README with architecture diagram + runtime choice justification
✅ Tests for: auth, agent create, workflow execute, message delivery, webhook enqueue
```

### Tradeoffs to document in the README, not solve

The README's "tradeoffs" section is where you explicitly *say* what you chose not to build and why:

```txt
- Picked Telegram for the channel — Slack would follow the same provider abstraction
- Used a sliding-window memory; vector memory is a future extension
- Cost tracking is in tokens, not USD — easy to multiply in the UI
- No streaming LLM responses in v1 — non-streaming keeps the runtime simpler and
  events fire at predictable boundaries
- Single Postgres instance — no replicas; reasonable for a local-first demo
```

This shows judgment without spending time.

### When in doubt

Ask:

1. Does this make the demo work? → do it
2. Does this make the architecture readable? → do it
3. Will the reviewer notice this missing? → maybe do it
4. Is this only valuable in production at 1000 users? → **do not do it**

### Rules

- Scope is fixed by the spec — the spec is law, your README is the negotiation
- Every "production-grade" feature outside the "Yes" list needs a README sentence justifying its absence (or presence)
- The two processes that exist are `api` and `worker`. No third process.
- One bot, one provider, one tool registry, one event schema — singular by default
- Premature abstractions cost the same time as building two of the thing — and only one is needed

See: [[arch-modular-monolith]], [[stack-choices]], [[ops-docker-compose]]
