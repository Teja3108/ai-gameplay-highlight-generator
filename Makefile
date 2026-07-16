.PHONY: help setup install-hooks lint lint-js lint-python format format-check test test-python dev-api dev-web docker-config docker-up

API_DIR := apps/api
UV := uv

help:
	@echo "Available targets:"
	@echo "  setup          Install dependencies and configure git hooks"
	@echo "  install-hooks  Install pre-commit git hooks"
	@echo "  lint           Run JavaScript and Python lint checks"
	@echo "  format         Auto-format JavaScript and Python sources"
	@echo "  format-check   Verify formatting without writing changes"
	@echo "  test           Run test suites"
	@echo "  dev-api        Start the API service with reload"
	@echo "  dev-web        Start the web application"
	@echo "  docker-config  Validate Docker Compose configuration"
	@echo "  docker-up      Build and start the API container"

setup:
	@test -f .env || cp .env.example .env
	npm install
	$(UV) sync --project $(API_DIR) --extra dev
	$(UV) run --project $(API_DIR) pre-commit install

install-hooks:
	$(UV) run --project $(API_DIR) pre-commit install

lint: lint-js lint-python

lint-js:
	npm run lint
	npm run typecheck
	npm run format:check

lint-python:
	cd $(API_DIR) && $(UV) run ruff check .
	cd $(API_DIR) && $(UV) run black --check .

format:
	npm run format
	cd $(API_DIR) && $(UV) run black .
	cd $(API_DIR) && $(UV) run ruff check --fix .

format-check: lint-js
	cd $(API_DIR) && $(UV) run black --check .
	cd $(API_DIR) && $(UV) run ruff check .

test: test-python

test-python:
	cd $(API_DIR) && $(UV) run pytest

dev-api:
	cd $(API_DIR) && $(UV) run uvicorn app.main:app --reload

dev-web:
	npm run dev:web

docker-config:
	docker compose config

docker-up:
	docker compose up --build api
