"""Source management API routes."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ego_data_core.connectors.source_service import SourceService, source_to_dict

router = APIRouter(prefix="/sources", tags=["sources"])

SourceType = Literal["filesystem", "screen", "browser", "operator", "sensor", "manual"]
PrivacyLevel = Literal["public", "private", "sensitive", "critical"]


class CreateSourceRequest(BaseModel):
    source_type: SourceType
    name: str = Field(min_length=1)
    root_uri: str = Field(min_length=1)
    privacy_level: PrivacyLevel = "private"
    scan_policy: dict[str, Any] = Field(default_factory=dict)
    retention_policy: dict[str, Any] = Field(default_factory=dict)


@router.get("")
def list_sources() -> dict[str, Any]:
    return SourceService().list_sources()


@router.post("")
def create_source(request: CreateSourceRequest) -> dict[str, Any]:
    source = SourceService().create_source(
        source_type=request.source_type,
        name=request.name,
        root_uri=request.root_uri,
        privacy_level=request.privacy_level,
        scan_policy=request.scan_policy,
        retention_policy=request.retention_policy,
    )
    return source_to_dict(source)
