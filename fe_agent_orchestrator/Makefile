.PHONY: install dev build run preview format format-check lint lint-fix typecheck analyze clean help \
	docker-build docker-run docker-stop docker-logs

PORT ?= 3000
DOCKER_PORT ?= 3000
LOG_DIR := logs
ANALYZE_LOG := $(LOG_DIR)/analyze.log
IMAGE ?= yuno/fe_agent_orchestrator
TAG ?= local
CONTAINER ?= fe_agent_orchestrator

help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	npm install

dev: ## Run the dev server (Vite, port $(PORT))
	npm run dev -- --port $(PORT)

build: ## Type-check and build for production
	npm run build

run: ## Build then serve the production bundle on port $(PORT)
	npm run build
	npm run preview -- --port $(PORT) --host 0.0.0.0

preview: ## Serve the existing production bundle on port $(PORT)
	npm run preview -- --port $(PORT) --host 0.0.0.0

format: ## Format the project with Prettier (120 col)
	npm run format

format-check: ## Check formatting without writing
	npm run format:check

lint: ## Run ESLint
	npm run lint

lint-fix: ## Run ESLint with --fix
	npm run lint:fix

typecheck: ## Run the TypeScript compiler (no emit)
	npm run typecheck

analyze: ## Run typecheck + lint + format-check, log to $(ANALYZE_LOG)
	@mkdir -p $(LOG_DIR)
	@echo "==> analyze started $$(date -u +%FT%TZ)" | tee $(ANALYZE_LOG)
	@echo "" | tee -a $(ANALYZE_LOG)
	@echo "==> typecheck" | tee -a $(ANALYZE_LOG)
	@(npm run typecheck 2>&1; echo "exit=$$?") | tee -a $(ANALYZE_LOG)
	@echo "" | tee -a $(ANALYZE_LOG)
	@echo "==> lint" | tee -a $(ANALYZE_LOG)
	@(npm run lint 2>&1; echo "exit=$$?") | tee -a $(ANALYZE_LOG)
	@echo "" | tee -a $(ANALYZE_LOG)
	@echo "==> format-check" | tee -a $(ANALYZE_LOG)
	@(npm run format:check 2>&1; echo "exit=$$?") | tee -a $(ANALYZE_LOG)
	@echo "" | tee -a $(ANALYZE_LOG)
	@echo "==> analyze finished $$(date -u +%FT%TZ) — log: $(ANALYZE_LOG)" | tee -a $(ANALYZE_LOG)

clean: ## Remove build artefacts and logs
	rm -rf dist $(LOG_DIR) node_modules/.tmp .vite

docker-build: ## Build the Docker image ($(IMAGE):$(TAG))
	docker build -t $(IMAGE):$(TAG) .

docker-run: ## Run the container on host port $(DOCKER_PORT)
	docker run --rm -d --name $(CONTAINER) -p $(DOCKER_PORT):3000 $(IMAGE):$(TAG)
	@echo "→ http://localhost:$(DOCKER_PORT)"

docker-stop: ## Stop and remove the container
	-docker stop $(CONTAINER)

docker-logs: ## Tail container logs
	docker logs -f $(CONTAINER)
