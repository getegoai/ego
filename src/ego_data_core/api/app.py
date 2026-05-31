"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from ego_data_core import __version__
from ego_data_core.api.routes.audit import router as audit_router
from ego_data_core.api.routes.health import router as health_router
from ego_data_core.api.routes.projects import router as projects_router
from ego_data_core.api.routes.sources import router as sources_router
from ego_data_core.api.routes.twin import router as twin_router
from ego_data_core.api.routes.workgraph import router as workgraph_router
from ego_data_core.storage.db import run_migrations


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ego Data Core Local API",
        version=__version__,
        description="Local-first API for Ego Data Core v0.1.",
        openapi_url="/openapi.json",
        lifespan=_lifespan,
    )
    app.include_router(audit_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(sources_router, prefix="/api/v1")
    app.include_router(twin_router, prefix="/api/v1")
    app.include_router(workgraph_router, prefix="/api/v1")
    return app


@asynccontextmanager
async def _lifespan(app: FastAPI):
    run_migrations()
    yield


app = create_app()
