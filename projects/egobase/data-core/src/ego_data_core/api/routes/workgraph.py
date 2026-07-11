"""Work graph extraction API routes."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ego_data_core.workgraph import (
    AutomationOpportunityService,
    WorkItemExtractor,
    work_item_to_dict,
)

router = APIRouter(prefix="/workgraph", tags=["workgraph"])

WorkItemType = Literal["task", "question", "risk"]
FeedbackAction = Literal["confirm", "reject", "edit", "later", "convert_to_task"]


class WorkItemFeedbackRequest(BaseModel):
    action: FeedbackAction
    title: str | None = Field(default=None)
    body: str | None = Field(default=None)


@router.post("/extract")
def extract_work_items() -> dict[str, Any]:
    return WorkItemExtractor().extract_items()


@router.get("/items")
def list_work_items() -> dict[str, Any]:
    return WorkItemExtractor().list_items()


@router.post("/automations/discover")
def discover_automation_opportunities() -> dict[str, Any]:
    return AutomationOpportunityService().discover_opportunities()


@router.get("/automations")
def list_automation_opportunities() -> dict[str, Any]:
    return AutomationOpportunityService().list_opportunities()


@router.post("/items/{item_type}/{item_id}/feedback")
def apply_work_item_feedback(
    item_type: WorkItemType,
    item_id: str,
    request: WorkItemFeedbackRequest,
) -> dict[str, Any]:
    item = WorkItemExtractor().apply_feedback(
        item_type,
        item_id,
        action=request.action,
        title=request.title,
        body=request.body,
    )
    return work_item_to_dict(item)
