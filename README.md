# Yuno — Agent Orchestrator

Multi-agent workflow platform with memory, real public-API tools, and a live workflow canvas. Backend in FastAPI + LangGraph + Postgres + Redis + Neo4j; frontend in React + Vite + React Flow.

## Quick start (single command)

```bash
cp .env.example .env
# paste at minimum: JWT_SECRET_KEY, OPENROUTER_API_KEY_MEMORY
docker compose up --build
```

That's it. The stack boots `fe + api + worker + postgres + redis + neo4j` with no external dependencies beyond the LLM / GitHub / Telegram calls the workflows themselves make.

### Ports

| Service    | Port        | What it serves                                |
|------------|-------------|-----------------------------------------------|
| `fe`       | `3000`      | The dashboard. Open `http://localhost:3000`   |
| `api`      | `3001`      | FastAPI, OpenAPI at `/api/v1/docs`            |
| `postgres` | `3002`      | App data + mem0 vectors (pgvector)            |
| `redis`    | `3003`      | arq queue + memory pub/sub                    |
| `neo4j`    | `3004/3005` | Graph store (Browser UI / Bolt)               |

The FE serves on `:3000` and proxies `/api/*` to the api container, so the browser sees a single origin and there are no CORS pre-flights.

## First-run sequence

1. **Sign up** in the FE — creates your user + a personal workspace.
2. **Add LLM provider keys** in the **LLM Providers** tab (OpenRouter recommended — one key gets you OpenAI / Anthropic / Gemini / open models).
3. **Seed the demo workflow:**
   ```bash
   docker compose exec api uv run python scripts/seed_github_concierge.py
   ```
   This installs 5 GitHub tools + 1 HN tool + 6 agents + 1 workflow, and auto-points your Telegram bot at the new workflow.
4. **(Optional) Add a GitHub PAT** for higher rate limits (5000 req/hr vs 60):
   ```bash
   docker compose exec postgres psql -U agent -d agent_orchestrator -p 3002 -c \
     "UPDATE tools SET auth_config = jsonb_build_object('token','ghp_xxx') WHERE slug LIKE 'github-%';"
   ```
5. **Test the workflow** from the dashboard: open the workflow detail page → right panel → **Test Run** tab → edit the JSON input → **Run**. Nodes light up live on the canvas.

## Telegram (optional)

The dashboard works without Telegram. To wire it:

1. Get a bot token from [@BotFather](https://t.me/BotFather).
2. Pick a random secret and set it as `TELEGRAM_WEBHOOK_SECRET` in `.env`.
3. Expose your api publicly (your own deploy URL, an ngrok tunnel, etc).
4. Tell Telegram about it:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<your-host>/api/v1/channels/telegram/webhook&secret_token=<SECRET>"
   ```
5. Send a message to your bot — the GitHub Concierge workflow runs end-to-end.

## Useful one-liners

```bash
docker compose ps                            # See what's up
docker compose logs -f api worker            # Tail the BE
docker compose down                          # Stop everything (keeps data)
docker compose down -v                       # Stop + nuke all volumes (DESTROYS data)

# Re-seed without restarting
docker compose exec api uv run python scripts/seed_github_concierge.py

# Apply a new migration
docker compose exec api uv run alembic upgrade head
```

## Architecture at a glance

- **Workflows** are DAGs (start → agent → condition → tool → end) compiled into `workflow_runs`. The `runtime/executor.py` walks the graph, calls per-node runners (`run_agent`, `run_tool`), and emits `runtime_events` row-by-row.
- **Agents** are LLM-backed nodes; each one references a `(provider, model)` and an optional list of `tools`. LLM keys resolve agent BYOK → workspace default → fail.
- **Tools** are typed callables — `builtin` (Python handler), `http`, `messaging`. The 5 GitHub tools + 1 HN tool ship as builtins.
- **Memory** is two layers: `agent_messages` for exact transcripts + mem0 (pgvector embeddings, Neo4j graph) for long-term facts. Writes happen once per workflow run.
- **Channels** today: Telegram webhook + a generic webhook ingress. Each agent can call `telegram-send` to reply.

For module-level docs, dig into `be_agent_orchestrator/app/modules/*/__init__.py` — every module has a one-paragraph "what this owns" header.

## Development (not docker)

The single-command compose is for demo / packaged distribution. For iterating on code, use the per-repo dev scripts:

- BE: `cd be_agent_orchestrator && make dev_no_reload` + `make worker_no_reload`
- FE: `cd fe_agent_orchestrator && npm run dev`

Both need the data layer up: `cd be_agent_orchestrator && docker compose up -d postgres redis neo4j` (uses the BE-local compose).
