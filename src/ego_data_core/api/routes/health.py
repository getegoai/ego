"""Health check routes."""

from __future__ import annotations

from fastapi import APIRouter

from ego_data_core import __version__
from ego_data_core.storage.db import get_database_status

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, object]:
    return {
        "status": "ok",
        "version": __version__,
        "database": get_database_status(),
    }
