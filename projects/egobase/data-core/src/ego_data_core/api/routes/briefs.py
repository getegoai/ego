"""Brief API routes."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel

from ego_data_core.brief import DailyBriefService, daily_brief_to_dict

router = APIRouter(prefix="/briefs", tags=["briefs"])

ReportType = Literal["daily"]
ReportFeedbackAction = Literal[
    "confirm",
    "reject",
    "edit",
    "later",
    "convert_to_task",
    "authorize_action",
]


class GenerateBriefRequest(BaseModel):
    report_type: ReportType = "daily"
    report_date: str | None = None
    force_regenerate: bool = False


class BriefItemFeedbackRequest(BaseModel):
    action: ReportFeedbackAction


@router.post("/generate")
def generate_brief(request: GenerateBriefRequest | None = None) -> dict[str, Any]:
    payload = request or GenerateBriefRequest()
    record = DailyBriefService().generate_daily_brief(
        payload.report_date,
        force_regenerate=payload.force_regenerate,
    )
    return daily_brief_to_dict(record)


@router.get("/daily/latest")
def get_latest_daily_brief() -> dict[str, Any] | None:
    record = DailyBriefService().get_latest_daily_brief()
    return daily_brief_to_dict(record) if record else None


@router.post("/items/{report_item_id}/feedback")
def apply_brief_item_feedback(
    report_item_id: str,
    request: BriefItemFeedbackRequest,
) -> dict[str, Any]:
    return DailyBriefService().apply_item_feedback(report_item_id, request.action)
