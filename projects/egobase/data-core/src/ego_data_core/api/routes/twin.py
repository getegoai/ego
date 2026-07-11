"""Ego Twin enhancement API routes."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from ego_data_core.twin import EnhancementService, MockOCRAdapter, ScreenshotOCRService

router = APIRouter(prefix="/twin", tags=["twin"])

EnhancementType = Literal["summary", "tag"]
EnhancementStrategy = Literal["auto", "local_only", "external_allowed"]
PrivacyLevel = Literal["public", "private", "sensitive", "critical"]
OCRAdapterName = Literal["unsupported", "mock"]


class CreateEnhancementJobRequest(BaseModel):
    evidence_ids: list[str] = Field(min_length=1)
    enhancement_type: EnhancementType
    strategy: EnhancementStrategy = "auto"
    privacy_level: PrivacyLevel | None = None
    priority: int = 2


class RunScreenshotOCRRequest(BaseModel):
    evidence_ids: list[str] = Field(min_length=1)
    adapter: OCRAdapterName = "unsupported"
    mock_text: str | None = None


@router.post("/enhance")
def create_enhancement_job(request: CreateEnhancementJobRequest) -> dict[str, Any]:
    job = EnhancementService().create_enhancement_job(
        evidence_ids=request.evidence_ids,
        enhancement_type=request.enhancement_type,
        strategy=request.strategy,
        privacy_level=request.privacy_level,
        priority=request.priority,
    )
    return {
        "job_id": job.job_id,
        "job_type": job.job_type,
        "status": job.status,
        "input": job.input,
        "priority": job.priority,
        "created_at": job.created_at,
    }


@router.get("/enhancements")
def list_enhancements(
    evidence_id: str | None = Query(default=None),
) -> dict[str, Any]:
    return EnhancementService().list_enhancements(evidence_id=evidence_id)


@router.post("/screens/ocr")
def run_screenshot_ocr(request: RunScreenshotOCRRequest) -> dict[str, Any]:
    adapter = None
    if request.adapter == "mock":
        adapter = MockOCRAdapter(text=request.mock_text or "Mock OCR text")
    return ScreenshotOCRService(adapter=adapter).enhance_screenshots(request.evidence_ids)
