"""Screenshot OCR enhancement pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from ego_data_core.audit.service import append_audit_log
from ego_data_core.kernel.id_generator import generate_id
from ego_data_core.storage.db import get_connection, run_migrations, transaction
from ego_data_core.vault import VaultStorage


OCR_TEXT_ENHANCEMENT_TYPE = "ocr_text"
SCREEN_STATE_ENHANCEMENT_TYPE = "screen_state"
COORDINATE_SPACE = "image_pixels"


@dataclass(frozen=True)
class OCRResult:
    status: str
    text: str = ""
    boxes: list[dict[str, Any]] = field(default_factory=list)
    regions: list[dict[str, Any]] = field(default_factory=list)
    confidence: float | None = None
    adapter_id: str = "unsupported"
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class OCRAdapter(Protocol):
    adapter_id: str

    def extract_text(
        self,
        image_path: Path,
        *,
        evidence: Mapping[str, Any],
    ) -> OCRResult:
        """Extract text from a screenshot image."""


class UnsupportedOCRAdapter:
    adapter_id = "unsupported"

    def extract_text(
        self,
        image_path: Path,
        *,
        evidence: Mapping[str, Any],
    ) -> OCRResult:
        return OCRResult(
            status="unsupported",
            text="",
            boxes=[],
            regions=[],
            confidence=None,
            adapter_id=self.adapter_id,
            error_message="No OCR adapter is configured.",
            metadata={"image_present": image_path.is_file()},
        )


class MockOCRAdapter:
    adapter_id = "mock"

    def __init__(
        self,
        *,
        text: str = "Mock OCR text",
        boxes: Sequence[Mapping[str, Any]] | None = None,
        regions: Sequence[Mapping[str, Any]] | None = None,
        confidence: float = 0.99,
    ) -> None:
        self.text = text
        self.boxes = [dict(item) for item in boxes] if boxes is not None else []
        self.regions = [dict(item) for item in regions] if regions is not None else []
        self.confidence = confidence

    def extract_text(
        self,
        image_path: Path,
        *,
        evidence: Mapping[str, Any],
    ) -> OCRResult:
        regions = self.regions or [
            {
                "region_id": "region_0",
                "bbox": {"x": 0, "y": 0, "width": None, "height": None},
                "text": self.text,
                "confidence": self.confidence,
            }
        ]
        boxes = self.boxes or [
            {
                "text": self.text,
                "bbox": {"x": 0, "y": 0, "width": None, "height": None},
                "confidence": self.confidence,
            }
        ]
        return OCRResult(
            status="succeeded",
            text=self.text,
            boxes=[dict(item) for item in boxes],
            regions=[dict(item) for item in regions],
            confidence=self.confidence,
            adapter_id=self.adapter_id,
            metadata={"image_present": image_path.is_file()},
        )


@dataclass(frozen=True)
class ScreenshotOCRItem:
    evidence_id: str
    status: str
    ocr_text_enhancement_id: str
    screen_state_enhancement_id: str
    text: str
    boxes: list[dict[str, Any]]
    regions: list[dict[str, Any]]
    adapter_id: str


class ScreenshotOCRService:
    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        storage: VaultStorage | None = None,
        adapter: OCRAdapter | None = None,
    ) -> None:
        self.database_path = database_path
        self.storage = storage or VaultStorage()
        self.adapter = adapter or UnsupportedOCRAdapter()

    def enhance_screenshots(self, evidence_ids: Sequence[str]) -> dict[str, Any]:
        normalized_ids = _normalize_evidence_ids(evidence_ids)
        rows = self._load_screenshot_evidence(normalized_ids)
        items = []
        for evidence_id in normalized_ids:
            evidence = rows[evidence_id]
            image_path = self.storage.resolve_uri(evidence["evidence_uri"])
            result = self.adapter.extract_text(image_path, evidence=evidence)
            items.append(self._write_enhancements(evidence, result))
        return {
            "items": [screenshot_ocr_item_to_dict(item) for item in items],
            "total": len(items),
        }

    def enhance_screenshot(self, evidence_id: str) -> ScreenshotOCRItem:
        result = self.enhance_screenshots([evidence_id])
        return _dict_to_item(result["items"][0])

    def _load_screenshot_evidence(
        self,
        evidence_ids: Sequence[str],
    ) -> dict[str, dict[str, Any]]:
        run_migrations(self.database_path)
        placeholders = ",".join("?" for _item in evidence_ids)
        with get_connection(self.database_path) as connection:
            rows = connection.execute(
                f"""
                SELECT
                  ev.*,
                  raw.title,
                  raw.metadata_json AS raw_metadata_json
                FROM evidence ev
                JOIN raw_objects raw ON raw.raw_object_id = ev.raw_object_id
                WHERE ev.evidence_id IN ({placeholders})
                """,
                list(evidence_ids),
            ).fetchall()

        rows_by_id = {row["evidence_id"]: _row_to_evidence_payload(row) for row in rows}
        missing = sorted(set(evidence_ids) - set(rows_by_id))
        if missing:
            raise ValueError(f"Evidence not found: {', '.join(missing)}")
        non_screenshots = sorted(
            evidence_id
            for evidence_id, row in rows_by_id.items()
            if row["evidence_type"] != "screenshot"
        )
        if non_screenshots:
            raise ValueError(
                "Evidence is not screenshot evidence: " + ", ".join(non_screenshots)
            )
        return rows_by_id

    def _write_enhancements(
        self,
        evidence: Mapping[str, Any],
        result: OCRResult,
    ) -> ScreenshotOCRItem:
        now = _utc_now()
        evidence_id = str(evidence["evidence_id"])
        ocr_text_enhancement_id = generate_id("enh")
        screen_state_enhancement_id = generate_id("enh")
        metadata = dict(evidence["metadata"])
        active_window = metadata.get("active_window")
        app_name = metadata.get("app_name")
        ocr_content = {
            "status": result.status,
            "text": result.text,
            "boxes": result.boxes,
            "regions": result.regions,
            "coordinate_space": COORDINATE_SPACE,
            "adapter_id": result.adapter_id,
            "error_message": result.error_message,
            "metadata": result.metadata,
        }
        screen_state_content = {
            "status": "succeeded",
            "ocr_status": result.status,
            "active_window": active_window,
            "app_name": app_name,
            "title": evidence["title"],
            "ocr_text_length": len(result.text),
            "regions": result.regions,
            "coordinate_space": COORDINATE_SPACE,
        }
        common_metadata = {
            "adapter_id": result.adapter_id,
            "evidence_type": evidence["evidence_type"],
            "raw_object_id": evidence["raw_object_id"],
            "version_id": evidence["version_id"],
            "coordinate_space": COORDINATE_SPACE,
        }

        with get_connection(self.database_path) as connection:
            with transaction(connection):
                _insert_enhancement(
                    connection,
                    enhancement_id=ocr_text_enhancement_id,
                    enhancement_type=OCR_TEXT_ENHANCEMENT_TYPE,
                    status=_enhancement_status_for_ocr(result.status),
                    content=ocr_content,
                    confidence=result.confidence,
                    privacy_level=evidence["privacy_level"],
                    metadata=common_metadata,
                    now=now,
                )
                _insert_enhancement(
                    connection,
                    enhancement_id=screen_state_enhancement_id,
                    enhancement_type=SCREEN_STATE_ENHANCEMENT_TYPE,
                    status="draft",
                    content=screen_state_content,
                    confidence=result.confidence,
                    privacy_level=evidence["privacy_level"],
                    metadata=common_metadata,
                    now=now,
                )
                _link_enhancement(connection, ocr_text_enhancement_id, evidence_id, now)
                _link_enhancement(connection, screen_state_enhancement_id, evidence_id, now)

        append_audit_log(
            "screenshot_ocr_generated",
            actor="system",
            target={"type": "evidence", "id": evidence_id},
            payload={
                "status": result.status,
                "adapter_id": result.adapter_id,
                "ocr_text_enhancement_id": ocr_text_enhancement_id,
                "screen_state_enhancement_id": screen_state_enhancement_id,
            },
            database_path=self.database_path,
        )
        return ScreenshotOCRItem(
            evidence_id=evidence_id,
            status=result.status,
            ocr_text_enhancement_id=ocr_text_enhancement_id,
            screen_state_enhancement_id=screen_state_enhancement_id,
            text=result.text,
            boxes=result.boxes,
            regions=result.regions,
            adapter_id=result.adapter_id,
        )


def screenshot_ocr_item_to_dict(item: ScreenshotOCRItem) -> dict[str, Any]:
    return {
        "evidence_id": item.evidence_id,
        "status": item.status,
        "ocr_text_enhancement_id": item.ocr_text_enhancement_id,
        "screen_state_enhancement_id": item.screen_state_enhancement_id,
        "text": item.text,
        "boxes": item.boxes,
        "regions": item.regions,
        "adapter_id": item.adapter_id,
    }


def _dict_to_item(payload: Mapping[str, Any]) -> ScreenshotOCRItem:
    return ScreenshotOCRItem(
        evidence_id=str(payload["evidence_id"]),
        status=str(payload["status"]),
        ocr_text_enhancement_id=str(payload["ocr_text_enhancement_id"]),
        screen_state_enhancement_id=str(payload["screen_state_enhancement_id"]),
        text=str(payload.get("text") or ""),
        boxes=list(payload.get("boxes") or []),
        regions=list(payload.get("regions") or []),
        adapter_id=str(payload["adapter_id"]),
    )


def _insert_enhancement(
    connection,
    *,
    enhancement_id: str,
    enhancement_type: str,
    status: str,
    content: Mapping[str, Any],
    confidence: float | None,
    privacy_level: str,
    metadata: Mapping[str, Any],
    now: str,
) -> None:
    connection.execute(
        """
        INSERT INTO enhancements(
          enhancement_id,
          enhancement_type,
          status,
          content_json,
          confidence,
          model_id,
          model_runtime,
          generated_at,
          privacy_level,
          metadata_json,
          created_at,
          updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            enhancement_id,
            enhancement_type,
            status,
            _to_json(content),
            confidence,
            metadata["adapter_id"],
            "ocr",
            now,
            privacy_level,
            _to_json(metadata),
            now,
            now,
        ),
    )


def _link_enhancement(
    connection,
    enhancement_id: str,
    evidence_id: str,
    now: str,
) -> None:
    connection.execute(
        """
        INSERT INTO enhancement_evidence_links(
          enhancement_id,
          evidence_id,
          weight,
          trace_note,
          created_at
        )
        VALUES (?, ?, 1.0, 'generated from screenshot evidence', ?)
        """,
        (enhancement_id, evidence_id, now),
    )


def _normalize_evidence_ids(evidence_ids: Sequence[str]) -> list[str]:
    normalized = [str(item).strip() for item in evidence_ids if str(item).strip()]
    if not normalized:
        raise ValueError("evidence_ids must not be empty")
    return list(dict.fromkeys(normalized))


def _row_to_evidence_payload(row) -> dict[str, Any]:
    return {
        "evidence_id": row["evidence_id"],
        "raw_object_id": row["raw_object_id"],
        "version_id": row["version_id"],
        "evidence_type": row["evidence_type"],
        "evidence_uri": row["evidence_uri"],
        "privacy_level": row["privacy_level"],
        "title": row["title"],
        "metadata": json.loads(row["metadata_json"]),
        "raw_metadata": json.loads(row["raw_metadata_json"]),
    }


def _enhancement_status_for_ocr(status: str) -> str:
    if status == "succeeded":
        return "draft"
    return "error"


def _to_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
