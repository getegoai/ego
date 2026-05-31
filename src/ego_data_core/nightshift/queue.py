"""SQLite-backed Night Shift job queue."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from ego_data_core.audit.service import append_audit_log
from ego_data_core.kernel.id_generator import generate_id
from ego_data_core.storage.db import get_connection, run_migrations, transaction


TERMINAL_JOB_STATUSES = frozenset({"succeeded", "failed", "blocked", "cancelled"})


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    job_type: str
    status: str
    priority: int
    input: dict[str, Any]
    output: dict[str, Any]
    policy: dict[str, Any]
    error_message: str | None
    retry_count: int
    max_retries: int
    scheduled_at: str | None
    started_at: str | None
    finished_at: str | None
    created_at: str
    updated_at: str


class NightShiftQueue:
    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = database_path

    def create_job(
        self,
        job_type: str,
        input: Mapping[str, Any] | None = None,
        *,
        priority: int = 2,
        policy: Mapping[str, Any] | None = None,
        max_retries: int = 3,
        scheduled_at: str | None = None,
    ) -> JobRecord:
        normalized_type = _normalize_job_type(job_type)
        now = _utc_now()
        job_id = generate_id("job")
        run_migrations(self.database_path)

        with get_connection(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO jobs(
                  job_id,
                  job_type,
                  status,
                  priority,
                  input_json,
                  output_json,
                  policy_json,
                  max_retries,
                  scheduled_at,
                  created_at,
                  updated_at
                )
                VALUES (?, ?, 'pending', ?, ?, '{}', ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    normalized_type,
                    int(priority),
                    _to_json(dict(input or {})),
                    _to_json(dict(policy or {})),
                    int(max_retries),
                    scheduled_at,
                    now,
                    now,
                ),
            )
            connection.commit()

        self._append_job_audit(
            "job_created",
            job_id,
            {
                "job_type": normalized_type,
                "status": "pending",
                "priority": int(priority),
            },
        )
        return self.get_job(job_id)

    def claim_next_job(self) -> JobRecord | None:
        run_migrations(self.database_path)
        now = _utc_now()
        claimed_id: str | None = None

        with get_connection(self.database_path) as connection:
            with transaction(connection):
                row = connection.execute(
                    """
                    SELECT job_id
                    FROM jobs
                    WHERE status = 'pending'
                      AND (scheduled_at IS NULL OR scheduled_at <= ?)
                    ORDER BY priority ASC, created_at ASC, job_id ASC
                    LIMIT 1
                    """,
                    (now,),
                ).fetchone()
                if row is None:
                    return None
                claimed_id = row["job_id"]
                connection.execute(
                    """
                    UPDATE jobs
                    SET status = 'running',
                        started_at = ?,
                        finished_at = NULL,
                        updated_at = ?
                    WHERE job_id = ? AND status = 'pending'
                    """,
                    (now, now, claimed_id),
                )

        if claimed_id is None:
            return None
        self._append_job_audit(
            "job_started",
            claimed_id,
            {"old_status": "pending", "new_status": "running"},
        )
        return self.get_job(claimed_id)

    def mark_succeeded(
        self,
        job_id: str,
        output: Mapping[str, Any] | None = None,
    ) -> JobRecord:
        now = _utc_now()
        old_status = self.get_job(job_id).status
        with get_connection(self.database_path) as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = 'succeeded',
                    output_json = ?,
                    error_message = NULL,
                    finished_at = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (_to_json(dict(output or {})), now, now, job_id),
            )
            connection.commit()

        self._append_job_audit(
            "job_succeeded",
            job_id,
            {"old_status": old_status, "new_status": "succeeded"},
        )
        return self.get_job(job_id)

    def mark_failed(self, job_id: str, error_message: str) -> JobRecord:
        now = _utc_now()
        current = self.get_job(job_id)
        next_retry_count = current.retry_count + 1
        will_retry = next_retry_count <= current.max_retries
        next_status = "pending" if will_retry else "failed"
        finished_at = None if will_retry else now
        started_at = None if will_retry else current.started_at

        with get_connection(self.database_path) as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = ?,
                    error_message = ?,
                    retry_count = ?,
                    scheduled_at = ?,
                    started_at = ?,
                    finished_at = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (
                    next_status,
                    error_message,
                    next_retry_count,
                    now if will_retry else current.scheduled_at,
                    started_at,
                    finished_at,
                    now,
                    job_id,
                ),
            )
            connection.commit()

        self._append_job_audit(
            "job_failed",
            job_id,
            {
                "old_status": current.status,
                "new_status": next_status,
                "will_retry": will_retry,
                "retry_count": next_retry_count,
                "max_retries": current.max_retries,
                "error": error_message,
            },
        )
        return self.get_job(job_id)

    def mark_blocked(self, job_id: str, reason: str | None = None) -> JobRecord:
        return self._mark_terminal(
            job_id,
            "blocked",
            "job_blocked",
            error_message=reason,
        )

    def cancel_job(self, job_id: str, reason: str | None = None) -> JobRecord:
        return self._mark_terminal(
            job_id,
            "cancelled",
            "job_cancelled",
            error_message=reason,
        )

    def get_job(self, job_id: str) -> JobRecord:
        run_migrations(self.database_path)
        with get_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            raise ValueError(f"Job not found: {job_id}")
        return _row_to_job(row)

    def _mark_terminal(
        self,
        job_id: str,
        status: str,
        event_type: str,
        *,
        error_message: str | None,
    ) -> JobRecord:
        if status not in TERMINAL_JOB_STATUSES:
            raise ValueError(f"Unsupported terminal status: {status}")
        now = _utc_now()
        old_status = self.get_job(job_id).status
        with get_connection(self.database_path) as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = ?,
                    error_message = ?,
                    finished_at = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (status, error_message, now, now, job_id),
            )
            connection.commit()

        self._append_job_audit(
            event_type,
            job_id,
            {
                "old_status": old_status,
                "new_status": status,
                "reason": error_message,
            },
        )
        return self.get_job(job_id)

    def _append_job_audit(
        self,
        event_type: str,
        job_id: str,
        payload: Mapping[str, Any],
    ) -> None:
        append_audit_log(
            event_type,
            actor="system",
            target={"type": "job", "id": job_id},
            payload=payload,
            database_path=self.database_path,
        )


def _row_to_job(row) -> JobRecord:
    return JobRecord(
        job_id=row["job_id"],
        job_type=row["job_type"],
        status=row["status"],
        priority=row["priority"],
        input=json.loads(row["input_json"]),
        output=json.loads(row["output_json"]),
        policy=json.loads(row["policy_json"]),
        error_message=row["error_message"],
        retry_count=row["retry_count"],
        max_retries=row["max_retries"],
        scheduled_at=row["scheduled_at"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _normalize_job_type(job_type: str) -> str:
    normalized = job_type.strip()
    if not normalized:
        raise ValueError("job_type must not be empty")
    return normalized


def _to_json(payload: Mapping[str, Any]) -> str:
    try:
        return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError(f"Job payload must be JSON serializable: {exc}") from exc


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
