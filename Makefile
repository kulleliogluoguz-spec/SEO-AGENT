.DEFAULT_GOAL := help
.PHONY: help up down build logs migrate seed test test-unit test-integration lint format clean health openapi

# ─── Colors ──────────────────────────────────────────────────────────────────
GREEN  := \033[0;32m
YELLOW := \033[0;33m
RESET  := \033[0m

help: ## Show this help message
	@echo "$(GREEN)AI CMO OS — Developer Commands$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-22s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ─── Docker ───────────────────────────────────────────────────────────────────
up: ## Start all services (build if needed)
	docker compose up --build -d
	@echo "$(GREEN)Services starting... run 'make logs' to watch$(RESET)"

down: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose restart

build: ## Rebuild all images
	docker compose build

logs: ## Tail all logs
	docker compose logs -f

logs-api: ## Tail API logs only
	docker compose logs -f api

logs-worker: ## Tail worker logs only
	docker compose logs -f worker

# ─── Database ─────────────────────────────────────────────────────────────────
migrate: ## Run database migrations
	docker compose exec api alembic upgrade head

migrate-down: ## Roll back last migration
	docker compose exec api alembic downgrade -1

migrate-create: ## Create new migration (NAME= required)
	@test -n "$(NAME)" || (echo "$(YELLOW)Usage: make migrate-create NAME=description$(RESET)" && exit 1)
	docker compose exec api alembic revision --autogenerate -m "$(NAME)"

migrate-history: ## Show migration history
	docker compose exec api alembic history --verbose

seed: ## Seed demo data
	docker compose exec api python scripts/seed_demo.py

reseed: ## Drop all data and reseed (DESTRUCTIVE)
	@echo "$(YELLOW)WARNING: This will drop and recreate all demo data$(RESET)"
	docker compose down -v
	docker compose up -d postgres redis
	@sleep 5
	$(MAKE) migrate
	$(MAKE) seed

# ─── Testing ──────────────────────────────────────────────────────────────────
test: ## Run all backend tests
	docker compose exec api pytest tests/ -v --tb=short

test-unit: ## Run unit tests only (fast, no DB)
	docker compose exec api pytest tests/unit/ -v --tb=short -m "not slow"

test-integration: ## Run integration tests
	docker compose exec api pytest tests/integration/ -v --tb=short

test-coverage: ## Run tests with HTML coverage report
	docker compose exec api pytest tests/ --cov=app --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)Coverage report: apps/api/htmlcov/index.html$(RESET)"

test-web: ## Run frontend tests
	cd apps/web && npm test -- --watchAll=false

# ─── Code Quality ─────────────────────────────────────────────────────────────
lint: ## Lint Python (ruff) and TypeScript (eslint)
	docker compose exec api ruff check app/ tests/
	cd apps/web && npm run lint

lint-fix: ## Auto-fix lint issues
	docker compose exec api ruff check --fix app/ tests/
	docker compose exec api ruff format app/ tests/

format: ## Format Python code
	docker compose exec api ruff format app/ tests/

typecheck: ## Run mypy type checking
	docker compose exec api mypy app/ --ignore-missing-imports

typecheck-web: ## Run TypeScript type check
	cd apps/web && npm run typecheck

# ─── Shells ───────────────────────────────────────────────────────────────────
shell-api: ## Shell into API container
	docker compose exec api bash

shell-db: ## Open psql session
	docker compose exec postgres psql -U aicmo -d aicmo

shell-redis: ## Open redis-cli session
	docker compose exec redis redis-cli

# ─── Health / Status ──────────────────────────────────────────────────────────
health: ## Check all service health
	@echo "$(GREEN)API liveness:$(RESET)"
	@curl -sf http://localhost:8000/health | python3 -m json.tool || echo "API not responding"
	@echo ""
	@echo "$(GREEN)API readiness:$(RESET)"
	@curl -sf http://localhost:8000/health/ready | python3 -m json.tool || echo "API not ready"
	@echo ""
	@echo "$(GREEN)Frontend:$(RESET)"
	@curl -sf -o /dev/null -w "HTTP %{http_code}\n" http://localhost:3000 || echo "Frontend not responding"

ps: ## Show running container status
	docker compose ps

openapi: ## Export OpenAPI spec to docs/
	curl -sf http://localhost:8000/openapi.json | python3 -m json.tool > docs/openapi.json
	@echo "$(GREEN)OpenAPI spec saved to docs/openapi.json$(RESET)"

# ─── Local Dev (no Docker) ────────────────────────────────────────────────────
dev-api: ## Run API locally without Docker
	cd apps/api && uvicorn app.main:app --reload --port 8000

dev-web: ## Run frontend locally without Docker
	cd apps/web && npm run dev

dev-worker: ## Run Temporal worker locally without Docker
	cd apps/api && python worker_main.py

install: ## Install all dependencies locally
	cd apps/api && pip install -r requirements.txt
	cd apps/web && npm install

# ─── Maintenance ─────────────────────────────────────────────────────────────
clean: ## Remove containers, volumes, and build artifacts (DESTRUCTIVE)
	@echo "$(YELLOW)WARNING: This removes all data volumes$(RESET)"
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)Clean complete$(RESET)"

