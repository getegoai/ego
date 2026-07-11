"""Manual screenshot import connector."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import mimetypes
from pathlib import Path
from typing import Any, Mapping

from ego_data_core.audit.service import append_audit_log
from ego_data_core.kernel.id_generator import generate_id
from ego_data_core.storage.db import get_connection, run_migrations, transaction
from ego_data_core.vault.storage import VaultStorage, build_vault_uri


SUPPORTED_IMAGE_MIME_TYPES = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/gif",
        "image/bmp",
    }
)


@dataclass(frozen=True)
class ScreenshotCaptureRecord:
    raw_object_id: str
    version_id: str
    evidence_id: str
    source_id: str
    title: str
    mime_type: str
    size_bytes: int
    content_hash: str
    storage_uri: str
    evidence_uri: str
    captured_at: str
    privacy_level: str
    metadata: dict[str, Any]


class ScreenCaptureService:
    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        storage: VaultStorage | None = None,
    ) -> None:
        self.database_path = database_path
        self.storage = storage or VaultStorage()

    def import_image_file(
        self,
        *,
        source_id: str,
        image_path: str | Path,
        active_window: str | None = None,
        app_name: str | None = None,
        captured_at: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ScreenshotCaptureRecord:
        run_migrations(self.database_path)
        path = Path(image_path).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"Screenshot image does not exist: {path}")

        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if mime_type not in SUPPORTED_IMAGE_MIME_TYPES:
            allowed = ", ".join(sorted(SUPPORTED_IMAGE_MIME_TYPES))
            raise ValueError(f"Unsupported screenshot MIME type '{mime_type}'. Allowed: {allowed}")

        stat = path.stat()
        content_hash = _sha256(path)
        now = _utc_now()
        captured = captured_at or now
        raw_object_id = generate_id("obj")
        version_id = generate_id("ver")
        evidence_id = generate_id("ev")

        with get_connection(self.database_path) as connection:
            source = _get_screen_source(connection, source_id)
            privacy_level = source["privacy_level"]

        storage_uri = self.storage.safe_copy_file(
            path,
            build_vault_uri("versions", f"{version_id}{path.suffix.lower()}"),
        )
        payload_metadata = {
            "capture_method": "manual_image_import",
            "connector": "screen_capture_v0",
            "original_filename": path.name,
            "active_window": active_window,
            "app_name": app_name,
            "screen_state": {
                "active_window": active_window,
                "app_name": app_name,
            },
            **dict(metadata or {}),
        }

        with get_connection(self.database_path) as connection:
            with transaction(connection):
                connection.execute(
                    """
                    INSERT INTO raw_objects(
                      raw_object_id,
                      source_id,
                      object_type,
                      original_uri,
                      canonical_uri,
                      content_hash,
                      size_bytes,
                      mime_type,
                      title,
                      created_at,
                      modified_at,
                      captured_at,
                      current_version_id,
                      status,
                      privacy_level,
                      metadata_json
                    )
                    VALUES (?, ?, 'screenshot', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                    """,
                    (
                        raw_object_id,
                        source_id,
                        path.as_uri(),
                        storage_uri,
                        content_hash,
                        stat.st_size,
                        mime_type,
                        path.name,
                        now,
                        _datetime_from_timestamp(stat.st_mtime),
                        captured,
                        version_id,
                        privacy_level,
                        _to_json(payload_metadata),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO object_versions(
                      version_id,
                      raw_object_id,
                      version_no,
                      storage_uri,
                      content_hash,
                      size_bytes,
                      captured_at,
                      metadata_json
                    )
                    VALUES (?, ?, 1, ?, ?, ?, ?, ?)
                    """,
                    (
                        version_id,
                        raw_object_id,
                        storage_uri,
                        content_hash,
                        stat.st_size,
                        captured,
                        _to_json(payload_metadata),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO evidence(
                      evidence_id,
                      raw_object_id,
                      version_id,
                      evidence_type,
                      evidence_uri,
                      evidence_selector_json,
                      captured_at,
                      content_hash,
                      privacy_level,
                      metadata_json,
                      created_at,
                      updated_at
                    )
                    VALUES (?, ?, ?, 'screenshot', ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        evidence_id,
                        raw_object_id,
                        version_id,
                        storage_uri,
                        _to_json({"type": "whole_screenshot"}),
                        captured,
                        content_hash,
                        privacy_level,
                        _to_json(payload_metadata),
                        now,
                        now,
                    ),
                )

        append_audit_log(
            "object_ingested",
            actor="system",
            target={"type": "raw_object", "id": raw_object_id},
            payload={
                "source_id": source_id,
                "object_type": "screenshot",
                "version_id": version_id,
                "content_hash": content_hash,
                "size_bytes": stat.st_size,
            },
            database_path=self.database_path,
        )
        append_audit_log(
            "evidence_created",
            actor="system",
            target={"type": "evidence", "id": evidence_id},
            payload={
                "source_id": source_id,
                "raw_object_id": raw_object_id,
                "version_id": version_id,
                "evidence_type": "screenshot",
                "content_hash": content_hash,
            },
            database_path=self.database_path,
        )
        return ScreenshotCaptureRecord(
            raw_object_id=raw_object_id,
            version_id=version_id,
            evidence_id=evidence_id,
            source_id=source_id,
            title=path.name,
            mime_type=mime_type,
            size_bytes=stat.st_size,
            content_hash=content_hash,
            storage_uri=storage_uri,
            evidence_uri=storage_uri,
            captured_at=captured,
            privacy_level=privacy_level,
            metadata=payload_metadata,
        )


def screenshot_capture_to_dict(record: ScreenshotCaptureRecord) -> dict[str, Any]:
    return {
        "raw_object_id": record.raw_object_id,
        "version_id": record.version_id,
        "evidence_id": record.evidence_id,
        "source_id": record.source_id,
        "title": record.title,
        "mime_type": record.mime_type,
        "size_bytes": record.size_bytes,
        "content_hash": record.content_hash,
        "storage_uri": record.storage_uri,
        "evidence_uri": record.evidence_uri,
        "captured_at": record.captured_at,
        "privacy_level": record.privacy_level,
        "metadata": record.metadata,
    }


def _get_screen_source(connection, source_id: str):
    row = connection.execute(
        "SELECT * FROM sources WHERE source_id = ?",
        (source_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Source not found: {source_id}")
    if row["source_type"] != "screen":
        raise ValueError(f"Source {source_id} is not a screen source")
    if not bool(row["enabled"]):
        raise ValueError(f"Source {source_id} is disabled")
    return row


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _datetime_from_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
