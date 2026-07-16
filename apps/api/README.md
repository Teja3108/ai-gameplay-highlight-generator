# API Service

Local FastAPI service that accepts gameplay video uploads and coordinates the existing local gameplay
engine. It is intentionally a single-user, local-only service: Docker Compose binds it to `127.0.0.1`,
and it must not be exposed to a network without authentication, durable job storage, and an ingress
security review.

## Run locally

From the repository root:

```bash
cp .env.example .env
# Set GAMEPLAY_ENGINE_ROOT and GAMEPLAY_ENGINE_PYTHON in .env.
uv sync --project apps/api --extra dev
uv run --project apps/api uvicorn app.main:app --reload
```

The service is available at `http://localhost:8000/api/health`. The browser client is expected to run
at `http://localhost:5173` by default.

## Quality checks

```bash
uv run --project apps/api --extra dev ruff check .
uv run --project apps/api --extra dev black --check .
uv run --project apps/api --extra dev pytest
```
