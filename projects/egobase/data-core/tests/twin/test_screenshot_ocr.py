from io import StringIO
import json
from pathlib import Path

import pytest

from ego_data_core.cli import run
from ego_data_core.connectors.filesystem import FilesystemScanner
from ego_data_core.connectors.screen import ScreenCaptureService
from ego_data_core.connectors.source_service import SourceService
from ego_data_core.storage.db import get_connection
from ego_data_core.twin import MockOCRAdapter, ScreenshotOCRService


PNG_BYTES = bytes.fromhex(
    "89504E470D0A1A0A"
    "0000000D4948445200000001000000010802000000907753DE"
    "0000000C49444154789C6360F8CF00000301010018DD8DB0"
    "0000000049454E44AE426082"
)


def test_screenshot_ocr_writes_unsupported_enhancement_without_ocr_environment(
    tmp_path: Path,
) -> None:
    capture = _prepare_screenshot(tmp_path)

    result = ScreenshotOCRService().enhance_screenshots([capture.evidence_id])

    assert result["total"] == 1
    item = result["items"][0]
    assert item["status"] == "unsupported"
    assert item["text"] == ""
    assert item["boxes"] == []
    assert item["regions"] == []

    enhancements = _enhancements_for_evidence(capture.evidence_id)
    ocr = enhancements["ocr_text"]
    screen_state = enhancements["screen_state"]
    ocr_content = json.loads(ocr["content_json"])
    screen_state_content = json.loads(screen_state["content_json"])

    assert ocr["status"] == "error"
    assert ocr_content["status"] == "unsupported"
    assert ocr_content["coordinate_space"] == "image_pixels"
    assert ocr_content["error_message"] == "No OCR adapter is configured."
    assert screen_state["status"] == "draft"
    assert screen_state_content["ocr_status"] == "unsupported"
    assert screen_state_content["active_window"] == "Ego Dashboard"
    assert screen_state_content["app_name"] == "Browser"

    with get_connection() as connection:
        audit_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM audit_logs
            WHERE event_type = 'screenshot_ocr_generated'
              AND subject_id = ?
            """,
            (capture.evidence_id,),
        ).fetchone()[0]
    assert audit_count == 1


def test_mock_screenshot_ocr_writes_text_boxes_regions_and_links_evidence(
    tmp_path: Path,
) -> None:
    capture = _prepare_screenshot(tmp_path)
    adapter = MockOCRAdapter(
        text="Alpha planning dashboard",
        boxes=[
            {
                "text": "Alpha",
                "bbox": {"x": 1, "y": 2, "width": 30, "height": 10},
                "confidence": 0.88,
            }
        ],
        regions=[
            {
                "region_id": "title",
                "bbox": {"x": 1, "y": 2, "width": 30, "height": 10},
                "text": "Alpha",
                "confidence": 0.88,
            }
        ],
        confidence=0.88,
    )

    result = ScreenshotOCRService(adapter=adapter).enhance_screenshots(
        [capture.evidence_id]
    )

    item = result["items"][0]
    assert item["status"] == "succeeded"
    assert item["text"] == "Alpha planning dashboard"
    assert item["boxes"][0]["bbox"]["x"] == 1
    assert item["regions"][0]["region_id"] == "title"

    enhancements = _enhancements_for_evidence(capture.evidence_id)
    ocr = enhancements["ocr_text"]
    screen_state = enhancements["screen_state"]
    ocr_content = json.loads(ocr["content_json"])
    screen_state_content = json.loads(screen_state["content_json"])

    assert ocr["status"] == "draft"
    assert ocr["confidence"] == 0.88
    assert ocr_content["text"] == "Alpha planning dashboard"
    assert ocr_content["boxes"][0]["text"] == "Alpha"
    assert screen_state_content["ocr_text_length"] == len("Alpha planning dashboard")
    assert screen_state_content["regions"][0]["region_id"] == "title"


def test_screenshot_ocr_api_creates_enhancements(client, tmp_path: Path) -> None:
    capture = _prepare_screenshot(tmp_path)

    response = client.post(
        "/api/v1/twin/screens/ocr",
        json={
            "evidence_ids": [capture.evidence_id],
            "adapter": "mock",
            "mock_text": "API OCR text",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["text"] == "API OCR text"

    listed = client.get(
        "/api/v1/twin/enhancements",
        params={"evidence_id": capture.evidence_id},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 2


def test_screen_ocr_cli_creates_mock_ocr_enhancement(tmp_path: Path) -> None:
    capture = _prepare_screenshot(tmp_path)
    stdout = StringIO()
    stderr = StringIO()

    status = run(
        [
            "screen",
            "ocr",
            capture.evidence_id,
            "--adapter",
            "mock",
            "--mock-text",
            "CLI OCR text",
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert status == 0, stderr.getvalue()
    payload = json.loads(stdout.getvalue())
    assert payload["total"] == 1
    assert payload["items"][0]["text"] == "CLI OCR text"


def test_screenshot_ocr_rejects_non_screenshot_evidence(
    sample_workspace: Path,
) -> None:
    source = SourceService().create_source(
        source_type="filesystem",
        name="Documents",
        root_uri=str(sample_workspace),
    )
    FilesystemScanner().scan_source(source.source_id)
    with get_connection() as connection:
        evidence_id = connection.execute(
            "SELECT evidence_id FROM evidence WHERE evidence_type = 'document' LIMIT 1"
        ).fetchone()["evidence_id"]

    with pytest.raises(ValueError, match="not screenshot evidence"):
        ScreenshotOCRService().enhance_screenshots([evidence_id])


def _prepare_screenshot(tmp_path: Path):
    image_path = tmp_path / "screen.png"
    image_path.write_bytes(PNG_BYTES)
    source = SourceService().create_source(
        source_type="screen",
        name="Manual Screen",
        root_uri="screen://manual",
        privacy_level="sensitive",
    )
    return ScreenCaptureService().import_image_file(
        source_id=source.source_id,
        image_path=image_path,
        active_window="Ego Dashboard",
        app_name="Browser",
    )


def _enhancements_for_evidence(evidence_id: str) -> dict[str, dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT enh.*
            FROM enhancements enh
            JOIN enhancement_evidence_links links
              ON links.enhancement_id = enh.enhancement_id
            WHERE links.evidence_id = ?
            ORDER BY enh.enhancement_type
            """,
            (evidence_id,),
        ).fetchall()
    return {row["enhancement_type"]: dict(row) for row in rows}
