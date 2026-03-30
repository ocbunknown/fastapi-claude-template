.PHONY: upgrade
upgrade: ## Run Alembic migrations
	alembic upgrade head

.PHONY: downgrade
downgrade: ## Rollback Alembic migrations
	alembic downgrade -1

.PHONY: generate
generate:
	alembic revision --autogenerate -m "$(NAME)"

.PHONY: docker_build
docker_build: ## Build Docker image
	docker compose build

.PHONY: docker_rebuild
docker_rebuild: ## Rebuild Docker image
	docker compose down
	docker compose build --no-cache

.PHONY: docker_up
docker_up: ## Run Docker container
	docker compose up -d

.PHONY: docker_dev_up
docker_dev_up: ## Run Docker container
	docker compose -f docker-compose.dev.yml up -d

.PHONY: docker_dev_rebuild
docker_dev_rebuild: ## Run Docker container
	docker compose -f docker-compose.dev.yml down
	docker compose -f docker-compose.dev.yml build --no-cache

.PHONY: docker_dev_down
docker_dev_down: ## Run Docker container
	docker compose -f docker-compose.dev.yml down

.PHONY: docker_down
docker_down: ## Stop Docker container
	docker compose down
