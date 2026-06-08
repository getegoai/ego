"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from ego_data_core import __version__
from ego_data_core.api.routes.actions import router as actions_router
from ego_data_core.api.routes.audit import router as audit_router
from ego_data_core.api.routes.briefs import router as briefs_router
from ego_data_core.api.routes.health import router as health_router
from ego_data_core.api.routes.projects import router as projects_router
from ego_data_core.api.routes.search import router as search_router
from ego_data_core.api.routes.screen import router as screen_router
from ego_data_core.api.routes.sources import router as sources_router
from ego_data_core.api.routes.twin import router as twin_router
from ego_data_core.api.routes.workgraph import router as workgraph_router
from ego_data_core.kernel.errors import (
    EgoError,
    ValidationError,
    error_payload,
    request_id_from_headers,
)
from ego_data_core.kernel.logging import get_logger, log_exception
from ego_data_core.storage.db import run_migrations

logger = get_logger(__name__)
UI_STATIC_DIR = Path(__file__).resolve().parent.parent / "ui" / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ego Data Core Local API",
        version=__version__,
        description="Local-first API for Ego Data Core v0.1.",
        openapi_url="/openapi.json",
        lifespan=_lifespan,
    )
    app.include_router(actions_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")
    app.include_router(briefs_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(search_router, prefix="/api/v1")
    app.include_router(screen_router, prefix="/api/v1")
    app.include_router(sources_router, prefix="/api/v1")
    app.include_router(twin_router, prefix="/api/v1")
    app.include_router(workgraph_router, prefix="/api/v1")
    _mount_static_ui(app)
    _register_exception_handlers(app)
    return app


@asynccontextmanager
async def _lifespan(app: FastAPI):
    run_migrations()
    yield


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(EgoError)
    async def ego_error_handler(request: Request, exc: EgoError) -> JSONResponse:
        return _json_error(request, exc)

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        error = ValidationError(
            "Request validation failed",
            code="request_validation_error",
            status_code=422,
            details={"error_count": len(exc.errors())},
        )
        return _json_error(request, error)

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return _json_error(request, ValidationError(str(exc)))

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        error = EgoError(
            str(exc.detail),
            code="http_error",
            status_code=exc.status_code,
        )
        return _json_error(request, error)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = request_id_from_headers(request.headers)
        log_exception(
            logger,
            "Unhandled API error",
            exc,
            context={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
            },
        )
        error = EgoError("Internal server error", code="internal_error", status_code=500)
        return JSONResponse(
            status_code=error.status_code,
            content=error_payload(error, request_id),
            headers={"x-request-id": request_id},
        )


def _mount_static_ui(app: FastAPI) -> None:
    if not UI_STATIC_DIR.exists():
        return

    @app.get("/", include_in_schema=False)
    def serve_local_ui() -> FileResponse:
        return FileResponse(UI_STATIC_DIR / "index.html")

    app.mount("/ui", StaticFiles(directory=UI_STATIC_DIR), name="ui")


def _json_error(request: Request, exc: EgoError) -> JSONResponse:
    request_id = request_id_from_headers(request.headers)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(exc, request_id),
        headers={"x-request-id": request_id},
    )


app = create_app()
