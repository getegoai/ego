"""Health check routes."""

from __future__ import annotations

from fastapi import APIRouter

from ego_data_core import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, object]:
    return {
        "status": "ok",
        "version": __version__,
        "database": {
            "status": "not_configured",
            "detail": "SQLite initialization is scheduled for EDC-001.",
        },
    }

