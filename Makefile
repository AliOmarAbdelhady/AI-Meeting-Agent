.PHONY: help install dev test lint format run migrate docker-up docker-down clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -e .

dev: ## Install development dependencies
	pip install -e ".[dev]"
	playwright install chromium

run: ## Start the development server
	uvicorn meeting_agent.asgi:app --reload --host 0.0.0.0 --port 8000

migrate: ## Run database migrations
	alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create msg="description")
	alembic revision --autogenerate -m "$(msg)"

test: ## Run all tests
	pytest tests/ -v

test-unit: ## Run unit tests only
	pytest tests/unit -v

test-integration: ## Run integration tests only
	pytest tests/integration -v

test-cov: ## Run tests with coverage report
	pytest tests/ -v --cov=meeting_agent --cov-report=html --cov-report=term

lint: ## Run linters
	ruff check src/ tests/
	mypy src/ --ignore-missing-imports

format: ## Format code
	ruff format src/ tests/
	ruff check --fix src/ tests/

docker-up: ## Start Docker containers
	docker compose -f docker/docker-compose.yml up -d

docker-down: ## Stop Docker containers
	docker compose -f docker/docker-compose.yml down

docker-build: ## Build Docker images
	docker compose -f docker/docker-compose.yml build

clean: ## Clean generated files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	rm -rf htmlcov/ .coverage
	rm -rf dist/ build/ *.egg-info
