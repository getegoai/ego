"""Append-only audit log service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping

from ego_data_core.kernel.id_generator import generate_id
from ego_data_core.storage.db import get_connection, run_migrations


KNOWN_AUDIT_EVENT_TYPES = frozenset(
    {
        "source_created",
        "object_ingested",
        "evidence_created",
        "job_created",
        "model_invoked",
        "policy_blocked",
        "brief_generated",
        "action_authorized",
        "error",
    }
)

VALID_ACTOR_TYPES = frozenset({"user", "system", "model", "operator"})


@dataclass(frozen=True)
class AuditActor:
    actor_type: str = "system"
    actor_id: str | None = None


@dataclass(frozen=True)
class AuditTarget:
    subject_type: str | None = None
    subject_id: str | None = None


@dataclass(frozen=True)
class AuditLogRecord:
    audit_id: str
    event_type: str
    actor_type: str
    actor_id: str | None
    subject_type: str | None
    subject_id: str | None
    event_time: str
    ip_or_device: str | None
    detail: dict[str, Any]
    prev_hash: str | None
    event_hash: str


class AuditService:
    """Append and query audit logs.

    The service intentionally exposes no update or delete methods.
    """

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = database_path

    def append_audit_log(
        self,
        event_type: str,
        actor: str | Mapping[str, str | None] | AuditActor = "system",
        target: Mapping[str, str | None] | AuditTarget | None = None,
        payload: Mapping[str, Any] | None = None,
        *,
        ip_or_device: str | None = None,
    ) -> AuditLogRecord:
        normalized_event_type = _normalize_event_type(event_type)
        normalized_actor = _normalize_actor(actor)
        normalized_target = _normalize_target(target)
        detail = dict(payload or {})
        detail_json = _to_json(detail)
        event_time = _utc_now()
        audit_id = generate_id("aud")

        run_migrations(self.database_path)
        with get_connection(self.database_path) as connection:
            prev_hash = _get_previous_event_hash(connection)
            event_hash = _event_hash(
                {
                    "audit_id": audit_id,
                    "event_type": normalized_event_type,
                    "actor_type": normalized_actor.actor_type,
                    "actor_id": normalized_actor.actor_id,
                    "subject_type": normalized_target.subject_type,
                    "subject_id": normalized_target.subject_id,
                    "event_time": event_time,
                    "ip_or_device": ip_or_device,
                    "detail_json": detail_json,
                    "prev_hash": prev_hash,
                }
            )
            connection.execute(
                """
                INSERT INTO audit_logs(
                  audit_id,
                  event_type,
                  actor_type,
                  actor_id,
                  subject_type,
                  subject_id,
                  event_time,
                  ip_or_device,
                  detail_json,
                  prev_hash,
                  event_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id,
                    normalized_event_type,
                    normalized_actor.actor_type,
                    normalized_actor.actor_id,
                    normalized_target.subject_type,
                    normalized_target.subject_id,
                    event_time,
                    ip_or_device,
                    detail_json,
                    prev_hash,
                    event_hash,
                ),
            )
            connection.commit()

        return AuditLogRecord(
            audit_id=audit_id,
            event_type=normalized_event_type,
            actor_type=normalized_actor.actor_type,
            actor_id=normalized_actor.actor_id,
            subject_type=normalized_target.subject_type,
            subject_id=normalized_target.subject_id,
            event_time=event_time,
            ip_or_device=ip_or_device,
            detail=detail,
            prev_hash=prev_hash,
            event_hash=event_hash,
        )

    def list_audit_logs(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        event_type: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
    ) -> dict[str, Any]:
        safe_limit = min(max(limit, 1), 200)
        safe_offset = max(offset, 0)
        run_migrations(self.database_path)

        where_clauses: list[str] = []
        params: list[Any] = []
        if event_type:
            where_clauses.append("event_type = ?")
            params.append(event_type)
        if subject_type:
            where_clauses.append("subject_type = ?")
            params.append(subject_type)
        if subject_id:
            where_clauses.append("subject_id = ?")
            params.append(subject_id)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        with get_connection(self.database_path) as connection:
            total = connection.execute(
                f"SELECT COUNT(*) FROM audit_logs {where_sql}",
                params,
            ).fetchone()[0]
            rows = connection.execute(
                f"""
                SELECT *
                FROM audit_logs
                {where_sql}
                ORDER BY rowid DESC
                LIMIT ? OFFSET ?
                """,
                [*params, safe_limit, safe_offset],
            ).fetchall()

        return {
            "items": [_row_to_record(row) for row in rows],
            "limit": safe_limit,
            "offset": safe_offset,
            "total": total,
        }


def append_audit_log(
    event_type: str,
    actor: str | Mapping[str, str | None] | AuditActor = "system",
    target: Mapping[str, str | None] | AuditTarget | None = None,
    payload: Mapping[str, Any] | None = None,
    *,
    database_path: str | Path | None = None,
    ip_or_device: str | None = None,
) -> AuditLogRecord:
    return AuditService(database_path).append_audit_log(
        event_type,
        actor,
        target,
        payload,
        ip_or_device=ip_or_device,
    )


def list_audit_logs(
    *,
    limit: int = 50,
    offset: int = 0,
    event_type: str | None = None,
    subject_type: str | None = None,
    subject_id: str | None = None,
    database_path: str | Path | None = None,
) -> dict[str, Any]:
    return AuditService(database_path).list_audit_logs(
        limit=limit,
        offset=offset,
        event_type=event_type,
        subject_type=subject_type,
        subject_id=subject_id,
    )


def _normalize_event_type(event_type: str) -> str:
    normalized = event_type.strip()
    if not normalized:
        raise ValueError("event_type must not be empty")
    return normalized


def _normalize_actor(actor: str | Mapping[str, str | None] | AuditActor) -> AuditActor:
    if isinstance(actor, AuditActor):
        normalized = actor
    elif isinstance(actor, str):
        normalized = AuditActor(actor_type=actor)
    else:
        normalized = AuditActor(
            actor_type=str(actor.get("type") or actor.get("actor_type") or "system"),
            actor_id=actor.get("id") or actor.get("actor_id"),
        )

    if normalized.actor_type not in VALID_ACTOR_TYPES:
        allowed = ", ".join(sorted(VALID_ACTOR_TYPES))
        raise ValueError(f"Invalid actor_type '{normalized.actor_type}'. Allowed: {allowed}")
    return normalized


def _normalize_target(
    target: Mapping[str, str | None] | AuditTarget | None,
) -> AuditTarget:
    if target is None:
        return AuditTarget()
    if isinstance(target, AuditTarget):
        return target
    return AuditTarget(
        subject_type=target.get("type") or target.get("subject_type"),
        subject_id=target.get("id") or target.get("subject_id"),
    )


def _to_json(payload: Mapping[str, Any]) -> str:
    try:
        return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError(f"Audit payload must be JSON serializable: {exc}") from exc


def _get_previous_event_hash(connection: sqlite3.Connection) -> str | None:
    row = connection.execute(
        "SELECT event_hash FROM audit_logs ORDER BY rowid DESC LIMIT 1"
    ).fetchone()
    return row["event_hash"] if row else None


def _event_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _row_to_record(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "audit_id": row["audit_id"],
        "event_type": row["event_type"],
        "actor_type": row["actor_type"],
        "actor_id": row["actor_id"],
        "subject_type": row["subject_type"],
        "subject_id": row["subject_id"],
        "event_time": row["event_time"],
        "ip_or_device": row["ip_or_device"],
        "detail": json.loads(row["detail_json"]),
        "prev_hash": row["prev_hash"],
        "event_hash": row["event_hash"],
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
