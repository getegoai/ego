"""Local evidence search API route."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ego_data_core.vault import LocalSearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search(
    q: str = Query(min_length=1),
    source_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    return LocalSearchService().search(
        q,
        source_id=source_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
