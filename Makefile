# TradeEasy Backend Makefile
# Provides convenient commands for development workflows

.PHONY: help dev up down logs clean test lint format

# Display help information
help:
	@echo "TradeEasy Backend Development Commands"
	@echo ""
	@echo "Usage:"
	@echo "  make dev           Start the local development environment"
	@echo "  make up            Start services in detached mode"
	@echo "  make down          Stop all services"
	@echo "  make logs          Follow the logs"
	@echo "  make clean         Stop all services and remove volumes"
	@echo "  make test          Run tests"
	@echo "  make lint          Run linting checks"
	@echo "  make format        Format code according to standards"
	@echo ""

# Start development environment
dev:
	docker-compose -f docker-compose.local.yml up

# Start in detached mode
up:
	docker-compose -f docker-compose.local.yml up -d

# Stop all services
down:
	docker-compose -f docker-compose.local.yml down

# Follow logs
logs:
	docker-compose -f docker-compose.local.yml logs -f

# Clean everything including volumes
clean:
	docker-compose -f docker-compose.local.yml down -v

# Run tests
test:
	docker-compose -f docker-compose.local.yml exec web pytest

# Run linting
lint:
	docker-compose -f docker-compose.local.yml exec web flake8 app tests

# Format code
format:
	docker-compose -f docker-compose.local.yml exec web black app tests
	docker-compose -f docker-compose.local.yml exec web isort app tests
