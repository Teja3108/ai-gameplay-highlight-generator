"""FastAPI application entry point.

Phase 0 intentionally defines no HTTP endpoints.
"""

from fastapi import FastAPI

from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="Gameplay Highlight Generator API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
