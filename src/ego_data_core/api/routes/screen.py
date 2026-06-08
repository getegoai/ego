"""Screen capture API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ego_data_core.connectors.screen import ScreenCaptureService, screenshot_capture_to_dict

router = APIRouter(prefix="/screen", tags=["screen"])


class ImportScreenshotRequest(BaseModel):
    source_id: str = Field(min_length=1)
    image_path: str = Field(min_length=1)
    active_window: str | None = None
    app_name: str | None = None
    captured_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("/import")
def import_screenshot(request: ImportScreenshotRequest) -> dict[str, Any]:
    record = ScreenCaptureService().import_image_file(
        source_id=request.source_id,
        image_path=request.image_path,
        active_window=request.active_window,
        app_name=request.app_name,
        captured_at=request.captured_at,
        metadata=request.metadata,
    )
    return screenshot_capture_to_dict(record)
