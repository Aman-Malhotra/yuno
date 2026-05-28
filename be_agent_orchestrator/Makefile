.DEFAULT_GOAL := help

PYTHON := uv run
APP    := app
TESTS  := tests

# ──────────────────────────────────────────────────────────────────────
# Help
# ──────────────────────────────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS=":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ──────────────────────────────────────────────────────────────────────
# Install
# ──────────────────────────────────────────────────────────────────────

.PHONY: install
install: ## Install runtime + dev deps via uv
	uv sync --group dev

.PHONY: lock
lock: ## Refresh uv.lock
	uv lock

# ──────────────────────────────────────────────────────────────────────
# Format / Lint / Types — "analysis"
# ──────────────────────────────────────────────────────────────────────

.PHONY: format
format: ## Format + autofix lint (ruff)
	$(PYTHON) ruff format $(APP) $(TESTS)
	$(PYTHON) ruff check --fix $(APP) $(TESTS)

.PHONY: lint
lint: ## Lint check only (no fix)
	$(PYTHON) ruff check $(APP) $(TESTS)
	$(PYTHON) ruff format --check $(APP) $(TESTS)

.PHONY: typecheck
typecheck: ## Run mypy --strict
	$(PYTHON) mypy $(APP)

.PHONY: analysis
analysis: lint typecheck ## Full static analysis (lint + types)

# ──────────────────────────────────────────────────────────────────────
# Build verification
# ──────────────────────────────────────────────────────────────────────

.PHONY: compile
compile: ## Byte-compile every module to catch syntax errors
	$(PYTHON) python -m compileall -q $(APP)

.PHONY: import-check
import-check: ## Import the FastAPI app to verify wiring
	$(PYTHON) python -c "from app.main import app; print(f'app loaded: {app.title}')"

.PHONY: build
build: install compile import-check analysis ## Full local build verification

# ──────────────────────────────────────────────────────────────────────
# OpenAPI export
# ──────────────────────────────────────────────────────────────────────

.PHONY: openapi
openapi: ## Dump the live OpenAPI spec to docs/openapi.json
	$(PYTHON) python scripts/export_openapi.py

.PHONY: docker-build
docker-build: ## Build the Docker image
	docker compose build

.PHONY: docker-build-verify
docker-build-verify: docker-build ## Build image + start stack briefly to confirm boot
	docker compose up -d postgres redis
	docker compose up -d api
	@sleep 5
	@curl -fsS http://localhost:3001/health || (echo "API not healthy"; exit 1)
	@echo "OK — api healthy on :3001"

# ──────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────

.PHONY: test
test: ## Run pytest
	$(PYTHON) pytest

.PHONY: test-cov
test-cov: ## Run pytest with coverage
	$(PYTHON) pytest --cov=$(APP) --cov-report=term-missing

# ──────────────────────────────────────────────────────────────────────
# DB / migrations
# ──────────────────────────────────────────────────────────────────────

.PHONY: migrate
migrate: ## Apply migrations
	$(PYTHON) alembic upgrade head

.PHONY: migration
migration: ## Generate a migration. Usage: make migration m="message"
	$(PYTHON) alembic revision --autogenerate -m "$(m)"

.PHONY: downgrade
downgrade: ## Roll back one migration
	$(PYTHON) alembic downgrade -1

.PHONY: seed
seed: ## Re-seed demo workspace (wipes + reinserts agents/tools/workflows + compiles)
	docker exec -i be_agent_orchestrator-postgres-1 \
		psql -U agent -d agent_orchestrator -p 3002 < scripts/seed_demo.sql
	$(PYTHON) python scripts/recompile_workflows.py

.PHONY: seed-github
seed-github: ## Seed the GitHub Concierge demo workflow (idempotent) + auto-update TELEGRAM_WORKFLOW_ID
	$(PYTHON) python scripts/seed_github_concierge.py

.PHONY: gh-pat
gh-pat: ## Paste a GitHub PAT into every github-* tool's auth_config. Usage: make gh-pat TOKEN=ghp_xxx
	@test -n "$(TOKEN)" || (echo "Usage: make gh-pat TOKEN=ghp_xxx" && exit 1)
	docker exec -i be_agent_orchestrator-postgres-1 \
		psql -U agent -d agent_orchestrator -p 3002 -c \
		"UPDATE tools SET auth_config = jsonb_build_object('token','$(TOKEN)') \
		 WHERE slug LIKE 'github-%';"

# ──────────────────────────────────────────────────────────────────────
# Local dev runners
# ──────────────────────────────────────────────────────────────────────

.PHONY: dev
dev: ## Run API with reload on :3001 (watches only app/)
	$(PYTHON) uvicorn app.main:app --host 0.0.0.0 --port 3001 --reload --reload-dir app

.PHONY: dev_no_reload
dev_no_reload: ## Run API on :3001 without reload (avoids restart-during-heavy-init issues)
	$(PYTHON) uvicorn app.main:app --host 0.0.0.0 --port 3001

.PHONY: worker
worker: ## Run Arq worker locally with hot-reload on app/ changes
	$(PYTHON) arq app.worker.arq_app.WorkerSettings --watch app

.PHONY: worker_no_reload
worker_no_reload: ## Run Arq worker without file watching
	$(PYTHON) arq app.worker.arq_app.WorkerSettings

# ──────────────────────────────────────────────────────────────────────
# Arq queue inspection (Redis on :3003)
# ──────────────────────────────────────────────────────────────────────

.PHONY: queue
queue: ## Show queue depth, pending jobs, in-progress, results
	@echo "── pending (score = scheduled-at, ms) ─────────────────"
	@redis-cli -p 3003 ZRANGE arq:queue 0 -1 WITHSCORES
	@echo "── queue depth ────────────────────────────────────────"
	@redis-cli -p 3003 ZCARD arq:queue
	@echo "── in-progress (held by a worker) ─────────────────────"
	@redis-cli -p 3003 --scan --pattern 'arq:in-progress:*'
	@echo "── results (completed/failed) ─────────────────────────"
	@redis-cli -p 3003 --scan --pattern 'arq:result:*'

.PHONY: queue-job
queue-job: ## Inspect one job + result by id (usage: make queue-job ID=abc123)
	@echo "── payload ────────────────────────────────────────────"
	@redis-cli -p 3003 GET arq:job:$(ID) || true
	@echo "── result ─────────────────────────────────────────────"
	@redis-cli -p 3003 GET arq:result:$(ID) || true

.PHONY: queue-flush
queue-flush: ## DANGER — drop every arq:* key (queue, jobs, results)
	@redis-cli -p 3003 --scan --pattern 'arq:*' | xargs -I {} redis-cli -p 3003 DEL {}

# ──────────────────────────────────────────────────────────────────────
# Docker compose lifecycle
# ──────────────────────────────────────────────────────────────────────

.PHONY: up
up: ## Start full stack (api + worker + postgres + redis)
	docker compose up -d --build

.PHONY: up-db
up-db: ## Start only postgres + redis
	docker compose up -d postgres redis

.PHONY: up-worker
up-worker: ## Start worker container (local-dev: API runs on host, worker in docker)
	docker compose up -d --build worker

.PHONY: worker-logs
worker-logs: ## Tail worker container logs
	docker compose logs -f worker

.PHONY: worker-restart
worker-restart: ## Restart worker (after job code changes)
	docker compose restart worker

.PHONY: down
down: ## Stop the stack (preserve volumes)
	docker compose down

.PHONY: nuke
nuke: ## Stop + remove volumes (DESTROYS the dev DB)
	docker compose down -v

.PHONY: logs
logs: ## Tail compose logs
	docker compose logs -f --tail=200

.PHONY: ps
ps: ## Show compose container status
	docker compose ps

# ──────────────────────────────────────────────────────────────────────
# Cleanup
# ──────────────────────────────────────────────────────────────────────

.PHONY: clean
clean: ## Remove caches
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -prune -exec rm -rf {} +
