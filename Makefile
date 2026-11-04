.PHONY: up down logs test lint migrate seed clean help

# Load .env if it exists (for local make targets that need env vars)
-include .env
export

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up: ## Build and start all services
	docker compose up --build -d

down: ## Stop all services
	docker compose down

logs: ## Tail logs for all services
	docker compose logs -f

test: ## Run all tests (API + worker)
	docker compose run --rm api ./gradlew test
	docker compose run --rm worker python -m pytest tests/ -v

lint: ## Run linters (ktlint for API, ruff for worker)
	docker compose run --rm api ./gradlew ktlintCheck
	docker compose run --rm worker python -m ruff check src/ tests/

migrate: ## Apply pending Flyway migrations against the running DB
	docker compose run --rm api ./gradlew flywayMigrate

seed: ## Load fixture data into the running DB
	@echo "No seed data yet — add scripts/seed.sql and update this target"

clean: ## Stop services and remove volumes (destroys all data)
	docker compose down -v
	@echo "All volumes removed. Run 'make up' to start fresh."
