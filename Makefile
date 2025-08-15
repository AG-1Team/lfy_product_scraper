# Makefile for Selenium Docker Project

.PHONY: help dev prod build up down logs clean rebuild test

# Default target
help:
	@echo "Available commands:"
	@echo "  dev      - Start in development mode with auto-reload"
	@echo "  prod     - Start in production mode"
	@echo "  build    - Build the Docker image"
	@echo "  up       - Start services (default docker-compose.yml)"
	@echo "  down     - Stop and remove containers"
	@echo "  logs     - Show logs"
	@echo "  clean    - Remove containers, networks, and images"
	@echo "  rebuild  - Rebuild and restart in dev mode"
	@echo "  test     - Test the setup"
	@echo "  shell    - Open shell in running container"

# Development mode with auto-reload
dev:
	@echo "Starting in development mode..."
	@mkdir -p data logs
	docker compose -f docker-compose.dev.yml up --build

# Production mode
prod:
	@echo "Starting in production mode..."
	@mkdir -p data logs
	docker compose -f docker-compose.prod.yml up -d --build

# Build the image
build:
	docker compose build

# Start with default compose file
up:
	@mkdir -p data logs
	docker compose up --build

# Stop services
down:
	docker compose down
	docker compose -f docker-compose.dev.yml down
	docker compose -f docker-compose.prod.yml down

# Show logs
logs:
	docker compose logs -f

# Clean everything
clean:
	docker compose down --rmi all --volumes --remove-orphans
	docker compose -f docker-compose.dev.yml down --rmi all --volumes --remove-orphans
	docker compose -f docker-compose.prod.yml down --rmi all --volumes --remove-orphans
	docker system prune -f

# Rebuild and restart in dev mode
rebuild:
	docker compose -f docker-compose.dev.yml down
	docker compose -f docker-compose.dev.yml up --build --force-recreate

# Test the setup
test:
	@echo "Testing system setup..."
	docker compose -f docker-compose.dev.yml run --rm selenium-app python -c "from src.driver.index import test_system_setup; test_system_setup()"

# Open shell in running container
shell:
	docker compose exec selenium-app bash

# Development with different options
dev-detached:
	@mkdir -p data logs
	docker compose -f docker-compose.dev.yml up -d --build

# View development logs
dev-logs:
	docker compose -f docker-compose.dev.yml logs -f

# Restart only the app service
restart:
	docker compose restart selenium-app
