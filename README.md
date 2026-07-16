# AI Gameplay Highlight Generator

A local-first monorepo for a gameplay-highlight generation platform. The web application uploads a
recording to the local FastAPI service, which orchestrates the existing gameplay engine CLI. This
repository is not a multi-user hosted service: do not expose its API to a network.

## Repository layout

```text
apps/
  api/             FastAPI service shell
  web/             React + TypeScript + Vite web application shell
  desktop/         Electron desktop application shell
packages/
  shared-types/    Shared TypeScript contracts package
```

## Prerequisites

- Node.js 20.18+ and npm 10.8+
- Python 3.9+
- [uv](https://docs.astral.sh/uv/) for Python dependency management
- Docker Desktop (optional, for containers)

## Setup

```bash
cp .env.example .env
npm install
uv sync --project apps/api --extra dev
```

## Common commands

```bash
# Web application
npm run dev:web

# Desktop shell
npm run dev:desktop

# API service (requires GAMEPLAY_ENGINE_ROOT and GAMEPLAY_ENGINE_PYTHON in .env)
uv run --project apps/api uvicorn app.main:app --reload

# Quality checks
npm run lint
npm run typecheck
npm run format:check
cd apps/api && uv run ruff check . && uv run black --check . && uv run pytest

# Container configuration / API service
docker compose config
docker compose up --build api
```

## Configuration

Environment defaults are documented in [`.env.example`](.env.example). Do not commit real environment files or credentials.

## License

Distributed under the [MIT License](LICENSE).
