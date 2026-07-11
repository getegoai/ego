"""Source management service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from ego_data_core.audit.service import append_audit_log
from ego_data_core.kernel.id_generator import generate_id
from ego_data_core.storage.db import get_connection, run_migrations, transaction


DEFAULT_USER_DISPLAY_NAME = "Local Ego User"


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    user_id: str
    device_id: str | None
    source_type: str
    name: str
    root_uri: str
    enabled: bool
    privacy_level: str
    scan_policy: dict[str, Any]
    retention_policy: dict[str, Any]
    created_at: str
    updated_at: str


class SourceService:
    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = database_path

    def create_source(
        self,
        *,
        source_type: str,
        name: str,
        root_uri: str,
        privacy_level: str = "private",
        scan_policy: Mapping[str, Any] | None = None,
        retention_policy: Mapping[str, Any] | None = None,
        device_id: str | None = None,
    ) -> SourceRecord:
        run_migrations(self.database_path)
        now = _utc_now()
        source_id = generate_id("src")
        scan_policy_json = _to_json(scan_policy or {})
        retention_policy_json = _to_json(retention_policy or {})

        with get_connection(self.database_path) as connection:
            user_id = _ensure_local_user(connection, now)
            with transaction(connection):
                connection.execute(
                    """
                    INSERT INTO sources(
                      source_id,
                      user_id,
                      device_id,
                      source_type,
                      name,
                      root_uri,
                      enabled,
                      privacy_level,
                      scan_policy_json,
                      retention_policy_json,
                      created_at,
                      updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_id,
                        user_id,
                        device_id,
                        source_type,
                        name,
                        root_uri,
                        privacy_level,
                        scan_policy_json,
                        retention_policy_json,
                        now,
                        now,
                    ),
                )

        append_audit_log(
            "source_created",
            actor="system",
            target={"type": "source", "id": source_id},
            payload={
                "source_id": source_id,
                "source_type": source_type,
                "name": name,
                "privacy_level": privacy_level,
            },
            database_path=self.database_path,
        )

        return SourceRecord(
            source_id=source_id,
            user_id=user_id,
            device_id=device_id,
            source_type=source_type,
            name=name,
            root_uri=root_uri,
            enabled=True,
            privacy_level=privacy_level,
            scan_policy=dict(scan_policy or {}),
            retention_policy=dict(retention_policy or {}),
            created_at=now,
            updated_at=now,
        )

    def list_sources(self) -> dict[str, Any]:
        run_migrations(self.database_path)
        with get_connection(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM sources
                ORDER BY created_at DESC, source_id DESC
                """
            ).fetchall()

        items = [_row_to_source(row) for row in rows]
        return {
            "items": [source_to_dict(item) for item in items],
            "total": len(items),
        }


def source_to_dict(source: SourceRecord) -> dict[str, Any]:
    return {
        "source_id": source.source_id,
        "user_id": source.user_id,
        "device_id": source.device_id,
        "source_type": source.source_type,
        "name": source.name,
        "root_uri": source.root_uri,
        "enabled": source.enabled,
        "privacy_level": source.privacy_level,
        "scan_policy": source.scan_policy,
        "retention_policy": source.retention_policy,
        "created_at": source.created_at,
        "updated_at": source.updated_at,
    }


def _ensure_local_user(connection, now: str) -> str:
    row = connection.execute(
        "SELECT user_id FROM users ORDER BY created_at LIMIT 1"
    ).fetchone()
    if row:
        return row["user_id"]

    user_id = generate_id("usr")
    connection.execute(
        """
        INSERT INTO users(user_id, display_name, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, DEFAULT_USER_DISPLAY_NAME, now, now),
    )
    return user_id


def _row_to_source(row) -> SourceRecord:
    return SourceRecord(
        source_id=row["source_id"],
        user_id=row["user_id"],
        device_id=row["device_id"],
        source_type=row["source_type"],
        name=row["name"],
        root_uri=row["root_uri"],
        enabled=bool(row["enabled"]),
        privacy_level=row["privacy_level"],
        scan_policy=json.loads(row["scan_policy_json"]),
        retention_policy=json.loads(row["retention_policy_json"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _to_json(payload: Mapping[str, Any]) -> str:
    try:
        return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError(f"Source policy must be JSON serializable: {exc}") from exc


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
