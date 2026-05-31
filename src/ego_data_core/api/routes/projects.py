"""Work graph project API routes."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ego_data_core.workgraph import ProjectDiscoveryService, project_to_dict

router = APIRouter(prefix="/projects", tags=["projects"])

ProjectFeedbackAction = Literal["confirm", "reject", "edit"]


class DiscoverProjectsRequest(BaseModel):
    force_regenerate: bool = False


class ProjectFeedbackRequest(BaseModel):
    action: ProjectFeedbackAction
    name: str | None = Field(default=None)
    summary: str | None = Field(default=None)


@router.post("/discover")
def discover_projects(request: DiscoverProjectsRequest | None = None) -> dict[str, Any]:
    force_regenerate = request.force_regenerate if request else False
    return ProjectDiscoveryService().discover_projects(
        force_regenerate=force_regenerate,
    )


@router.get("")
def list_projects() -> dict[str, Any]:
    return ProjectDiscoveryService().list_projects()


@router.post("/{project_id}/feedback")
def apply_project_feedback(
    project_id: str,
    request: ProjectFeedbackRequest,
) -> dict[str, Any]:
    project = ProjectDiscoveryService().apply_feedback(
        project_id,
        action=request.action,
        name=request.name,
        summary=request.summary,
    )
    return project_to_dict(project)
