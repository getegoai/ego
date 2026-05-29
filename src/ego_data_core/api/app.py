"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from ego_data_core import __version__
from ego_data_core.api.routes.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ego Data Core Local API",
        version=__version__,
        description="Local-first API for Ego Data Core v0.1.",
        openapi_url="/openapi.json",
    )
    app.include_router(health_router, prefix="/api/v1")
    return app


app = create_app()

