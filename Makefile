.PHONY: help setup install env start stop up up-d down restart logs ps health test test-cov lint format dev clean

PYTHON ?= python3
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
UVICORN := $(PYTHON) -m uvicorn
BLACK := $(PYTHON) -m black
RUFF := $(PYTHON) -m ruff

help:
	@echo "KABAN AI — make targets"
	@echo ""
	@echo "  make start     Full startup: AI provider + Docker stack"
	@echo "  make stop      Stop Docker stack"
	@echo "  make setup     Install Python deps + create .env"
	@echo "  make up        Build and start Docker stack (foreground)"
	@echo "  make up-d      Build and start Docker stack (detached)"
	@echo "  make down      Stop Docker stack"
	@echo "  make restart   Restart Docker stack"
	@echo "  make logs      Follow container logs"
	@echo "  make ps        Show container status"
	@echo "  make health    Check /api/health"
	@echo "  make test      Run tests"
	@echo "  make test-cov  Run tests with 100% coverage check"
	@echo "  make lint      Ruff + Black check"
	@echo "  make format    Black format + Ruff fix"
	@echo "  make dev       Run backend locally (no Docker)"
	@echo "  make clean     Remove pytest cache"

setup: install env

install:
	$(PIP) install -r backend/requirements.txt -r test/requirements.txt

env:
	@test -f .env || cp .env.example .env

start: env
	@chmod +x scripts/start.sh
	@./scripts/start.sh

stop:
	@chmod +x scripts/stop.sh
	@./scripts/stop.sh

up: env
	docker compose up --build

up-d: env
	docker compose up --build -d

down:
	docker compose down

restart: down up-d

logs:
	docker compose logs -f

ps:
	docker compose ps

health:
	@curl -sf http://localhost:8080/api/health && echo

test: install
	$(PYTEST) test/ -q

test-cov: install
	$(PYTEST) test/ --cov=backend --cov-branch --cov-report=term-missing --cov-fail-under=100

lint: install
	$(RUFF) check backend test
	$(BLACK) --check backend test

format: install
	$(BLACK) backend test
	$(RUFF) check backend test --fix

dev: env install
	cd backend && $(UVICORN) app:app --host 0.0.0.0 --port 8000 --reload

clean:
	rm -rf .pytest_cache
	find test -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
