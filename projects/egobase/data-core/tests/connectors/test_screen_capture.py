from io import StringIO
import json
from pathlib import Path

import pytest

from ego_data_core.cli import run
from ego_data_core.connectors.screen import ScreenCaptureService
from ego_data_core.connectors.source_service import SourceService
from ego_data_core.storage.db import get_connection
from ego_data_core.vault import VaultStorage


PNG_BYTES = bytes.fromhex(
    "89504E470D0A1A0A"
    "0000000D4948445200000001000000010802000000907753DE"
    "0000000C49444154789C6360F8CF00000301010018DD8DB0"
    "0000000049454E44AE426082"
)


def test_import_image_file_creates_screenshot_object_version_and_evidence(
    tmp_path: Path,
) -> None:
    image_path = _make_png(tmp_path)
    source = _create_screen_source()

    record = ScreenCaptureService().import_image_file(
        source_id=source.source_id,
        image_path=image_path,
        active_window="Ego Dashboard",
        app_name="Browser",
        metadata={"region": {"x": 0, "y": 0, "width": 1, "height": 1}},
    )

    assert record.raw_object_id.startswith("obj_")
    assert record.version_id.startswith("ver_")
    assert record.evidence_id.startswith("ev_")
    assert record.mime_type == "image/png"
    assert record.privacy_level == "sensitive"
    assert record.metadata["active_window"] == "Ego Dashboard"
    assert record.metadata["app_name"] == "Browser"
    assert record.metadata["screen_state"] == {
        "active_window": "Ego Dashboard",
        "app_name": "Browser",
    }
    assert VaultStorage().resolve_uri(record.storage_uri).is_file()

    with get_connection() as connection:
        raw = connection.execute(
            "SELECT * FROM raw_objects WHERE raw_object_id = ?",
            (record.raw_object_id,),
        ).fetchone()
        version = connection.execute(
            "SELECT * FROM object_versions WHERE version_id = ?",
            (record.version_id,),
        ).fetchone()
        evidence = connection.execute(
            "SELECT * FROM evidence WHERE evidence_id = ?",
            (record.evidence_id,),
        ).fetchone()
        audit_events = [
            row["event_type"]
            for row in connection.execute(
                "SELECT event_type FROM audit_logs ORDER BY event_time"
            ).fetchall()
        ]

    assert raw["object_type"] == "screenshot"
    assert raw["current_version_id"] == record.version_id
    assert json.loads(raw["metadata_json"])["connector"] == "screen_capture_v0"
    assert version["storage_uri"] == record.storage_uri
    assert evidence["evidence_type"] == "screenshot"
    assert evidence["evidence_uri"] == record.storage_uri
    assert json.loads(evidence["evidence_selector_json"]) == {"type": "whole_screenshot"}
    assert "object_ingested" in audit_events
    assert "evidence_created" in audit_events


def test_screen_import_api_does_not_return_original_absolute_path(
    client,
    tmp_path: Path,
) -> None:
    image_path = _make_png(tmp_path)
    source_response = client.post(
        "/api/v1/sources",
        json={
            "source_type": "screen",
            "name": "Manual Screenshots",
            "root_uri": "screen://manual",
            "privacy_level": "private",
        },
    )
    source_id = source_response.json()["source_id"]

    response = client.post(
        "/api/v1/screen/import",
        json={
            "source_id": source_id,
            "image_path": str(image_path),
            "active_window": "Notes",
            "app_name": "Editor",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    payload_text = json.dumps(payload, ensure_ascii=True)
    assert payload["evidence_id"].startswith("ev_")
    assert payload["metadata"]["active_window"] == "Notes"
    assert payload["storage_uri"].startswith("vault://versions/")
    assert str(image_path.resolve()) not in payload_text
    assert image_path.resolve().as_uri() not in payload_text


def test_screen_import_cli_returns_screenshot_evidence(tmp_path: Path) -> None:
    image_path = _make_png(tmp_path)
    source = _create_screen_source()
    stdout = StringIO()
    stderr = StringIO()

    status = run(
        [
            "screen",
            "import",
            str(image_path),
            "--source-id",
            source.source_id,
            "--active-window",
            "Terminal",
            "--app-name",
            "Windows Terminal",
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert status == 0, stderr.getvalue()
    payload = json.loads(stdout.getvalue())
    assert payload["evidence_id"].startswith("ev_")
    assert payload["metadata"]["app_name"] == "Windows Terminal"
    assert payload["evidence_uri"].startswith("vault://versions/")


def test_import_rejects_non_screen_source_and_unsupported_file(tmp_path: Path) -> None:
    image_path = _make_png(tmp_path)
    text_path = tmp_path / "not-a-screenshot.txt"
    text_path.write_text("plain text", encoding="utf-8")
    filesystem_source = SourceService().create_source(
        source_type="filesystem",
        name="Documents",
        root_uri=str(tmp_path),
    )
    screen_source = _create_screen_source()
    service = ScreenCaptureService()

    with pytest.raises(ValueError, match="is not a screen source"):
        service.import_image_file(source_id=filesystem_source.source_id, image_path=image_path)

    with pytest.raises(ValueError, match="Unsupported screenshot MIME type"):
        service.import_image_file(source_id=screen_source.source_id, image_path=text_path)


def _create_screen_source():
    return SourceService().create_source(
        source_type="screen",
        name="Manual Screen",
        root_uri="screen://manual",
        privacy_level="sensitive",
    )


def _make_png(tmp_path: Path) -> Path:
    image_path = tmp_path / "capture.png"
    image_path.write_bytes(PNG_BYTES)
    return image_path
