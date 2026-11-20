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
	(cd api && ./gradlew test)
	(cd worker && pytest tests/ -v)

lint: ## Run linters (ktlint for API, ruff for worker)
	(cd api && ./gradlew ktlintCheck)
	(cd worker && ruff check src/ tests/)

migrate: ## Apply pending Flyway migrations against the running DB
	docker compose run --rm api ./gradlew flywayMigrate

seed: ## Load fixture data into the running DB
	@echo "No seed data yet — add scripts/seed.sql and update this target"

clean: ## Stop services and remove volumes (destroys all data)
	docker compose down -v
	@echo "All volumes removed. Run 'make up' to start fresh."
