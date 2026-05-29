"""Audit log API routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ego_data_core.audit.service import list_audit_logs

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs")
def get_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = None,
    subject_type: str | None = None,
    subject_id: str | None = None,
) -> dict[str, object]:
    return list_audit_logs(
        limit=limit,
        offset=offset,
        event_type=event_type,
        subject_type=subject_type,
        subject_id=subject_id,
    )
