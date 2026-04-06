PYTHON ?= uv run
COMPOSE ?= docker compose
COMPOSE_DEV ?= docker compose -f docker-compose.dev.yml

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install all dependencies
	uv sync --all-groups

.PHONY: sync
sync: ## Sync runtime dependencies
	uv sync --frozen --no-dev

.PHONY: lock
lock: ## Refresh uv.lock
	uv lock

.PHONY: upgrade
upgrade: ## Apply Alembic migrations
	$(PYTHON) alembic upgrade head

.PHONY: downgrade
downgrade: ## Rollback last Alembic migration
	$(PYTHON) alembic downgrade -1

.PHONY: generate
generate: ## Autogenerate Alembic revision (NAME=...)
	$(PYTHON) alembic revision --autogenerate -m "$(NAME)"

.PHONY: history
history: ## Show Alembic history
	$(PYTHON) alembic history

.PHONY: run-http
run-http: ## Run HTTP API
	$(PYTHON) python -m src.entrypoints.http

.PHONY: run-consumers
run-consumers: ## Run message consumers
	$(PYTHON) faststream run src.entrypoints.consumers:app

.PHONY: run-worker
run-worker: ## Run Taskiq worker
	$(PYTHON) taskiq worker src.entrypoints.tasks:broker

.PHONY: run-scheduler
run-scheduler: ## Run Taskiq scheduler
	$(PYTHON) taskiq scheduler src.entrypoints.tasks:scheduler

.PHONY: lint
lint: ## Run ruff linter
	$(PYTHON) ruff check src tests

.PHONY: format
format: ## Format code
	$(PYTHON) ruff format src tests
	$(PYTHON) ruff check --fix src tests

.PHONY: typecheck
typecheck: ## Run mypy
	$(PYTHON) mypy src

.PHONY: check
check: lint typecheck ## Run static checks

.PHONY: test
test: ## Run all tests
	$(PYTHON) pytest

.PHONY: test-unit
test-unit: ## Run unit tests
	$(PYTHON) pytest -m unit

.PHONY: test-integration
test-integration: ## Run integration tests
	$(PYTHON) pytest -m integration

.PHONY: test-e2e
test-e2e: ## Run e2e tests
	$(PYTHON) pytest -m e2e

.PHONY: docker-build
docker-build: ## Build production images
	$(COMPOSE) build

.PHONY: docker-rebuild
docker-rebuild: ## Rebuild production images
	$(COMPOSE) down
	$(COMPOSE) build --no-cache

.PHONY: docker-up
docker-up: ## Start full stack
	$(COMPOSE) up -d

.PHONY: docker-down
docker-down: ## Stop full stack
	$(COMPOSE) down

.PHONY: docker-logs
docker-logs: ## Tail logs
	$(COMPOSE) logs -f

.PHONY: docker-migrate
docker-migrate: ## Run migrations in container
	$(COMPOSE) run --rm migrate

.PHONY: docker-dev-up
docker-dev-up: ## Start dev infra
	$(COMPOSE_DEV) up -d

.PHONY: docker-dev-down
docker-dev-down: ## Stop dev infra
	$(COMPOSE_DEV) down

.PHONY: docker-dev-rebuild
docker-dev-rebuild: ## Rebuild dev infra
	$(COMPOSE_DEV) down
	$(COMPOSE_DEV) build --no-cache

.PHONY: docker-dev-logs
docker-dev-logs: ## Tail dev infra logs
	$(COMPOSE_DEV) logs -f
