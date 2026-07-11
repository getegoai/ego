"""Data health snapshot for Daily Brief reports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from ego_data_core.kernel.time import local_date_bounds_as_utc, normalize_report_date
from ego_data_core.storage.db import get_connection, run_migrations


@dataclass(frozen=True)
class DataHealthSnapshot:
    report_date: str
    new_file_count: int
    evidence_count: int
    parsed_version_count: int
    parse_failed_count: int
    parse_pending_count: int
    parse_success_rate: float | None
    enhancement_job_count: int
    enhancement_succeeded_count: int
    enhancement_failed_count: int
    enhancement_pending_count: int
    enhancement_success_rate: float | None
    enhanced_evidence_count: int
    unenhanced_evidence_count: int
    policy_blocked_count: int
    failed_jobs: list[dict[str, Any]]
    pending_jobs: list[dict[str, Any]]
    recommendations: list[str]
    severity: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_date": self.report_date,
            "new_file_count": self.new_file_count,
            "evidence_count": self.evidence_count,
            "parsed_version_count": self.parsed_version_count,
            "parse_failed_count": self.parse_failed_count,
            "parse_pending_count": self.parse_pending_count,
            "parse_success_rate": self.parse_success_rate,
            "enhancement_job_count": self.enhancement_job_count,
            "enhancement_succeeded_count": self.enhancement_succeeded_count,
            "enhancement_failed_count": self.enhancement_failed_count,
            "enhancement_pending_count": self.enhancement_pending_count,
            "enhancement_success_rate": self.enhancement_success_rate,
            "enhanced_evidence_count": self.enhanced_evidence_count,
            "unenhanced_evidence_count": self.unenhanced_evidence_count,
            "policy_blocked_count": self.policy_blocked_count,
            "failed_jobs": self.failed_jobs,
            "pending_jobs": self.pending_jobs,
            "recommendations": self.recommendations,
            "severity": self.severity,
        }


class DataHealthService:
    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = database_path

    def snapshot(self, report_date: str) -> DataHealthSnapshot:
        run_migrations(self.database_path)
        target_date = _normalize_date(report_date)
        start, end = _date_bounds(target_date)
        with get_connection(self.database_path) as connection:
            evidence_stats = _fetch_one_dict(
                connection,
                """
                SELECT
                  COUNT(DISTINCT ev.evidence_id) AS evidence_count,
                  COUNT(DISTINCT raw.raw_object_id) AS new_file_count
                FROM evidence ev
                JOIN raw_objects raw ON raw.raw_object_id = ev.raw_object_id
                WHERE ev.captured_at >= ? AND ev.captured_at < ?
                  AND raw.object_type = 'file'
                """,
                (start, end),
            )
            parse_stats = _fetch_one_dict(
                connection,
                """
                SELECT
                  COUNT(*) AS version_count,
                  SUM(CASE WHEN extracted_text_uri IS NOT NULL THEN 1 ELSE 0 END)
                    AS parsed_version_count
                FROM object_versions
                WHERE captured_at >= ? AND captured_at < ?
                """,
                (start, end),
            )
            parse_failed_count = int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM jobs
                    WHERE job_type = 'document_parse'
                      AND status = 'failed'
                      AND created_at >= ? AND created_at < ?
                    """,
                    (start, end),
                ).fetchone()[0]
            )
            enhancement_stats = _fetch_one_dict(
                connection,
                """
                SELECT
                  COUNT(*) AS job_count,
                  SUM(CASE WHEN status = 'succeeded' THEN 1 ELSE 0 END) AS succeeded_count,
                  SUM(CASE WHEN status IN ('failed','blocked','cancelled') THEN 1 ELSE 0 END)
                    AS failed_count,
                  SUM(CASE WHEN status IN ('pending','running') THEN 1 ELSE 0 END)
                    AS pending_count
                FROM jobs
                WHERE job_type = 'enhance_evidence'
                  AND created_at >= ? AND created_at < ?
                """,
                (start, end),
            )
            enhanced_evidence_count = int(
                connection.execute(
                    """
                    SELECT COUNT(DISTINCT ev.evidence_id)
                    FROM evidence ev
                    JOIN enhancement_evidence_links link
                      ON link.evidence_id = ev.evidence_id
                    WHERE ev.captured_at >= ? AND ev.captured_at < ?
                    """,
                    (start, end),
                ).fetchone()[0]
            )
            policy_blocked_count = int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM audit_logs
                    WHERE event_type = 'policy_blocked'
                      AND event_time >= ? AND event_time < ?
                    """,
                    (start, end),
                ).fetchone()[0]
            )
            failed_jobs = _fetch_job_dicts(
                connection,
                """
                SELECT *
                FROM jobs
                WHERE status IN ('failed','blocked')
                  AND created_at >= ? AND created_at < ?
                ORDER BY created_at DESC, job_id DESC
                LIMIT 5
                """,
                (start, end),
            )
            pending_jobs = _fetch_job_dicts(
                connection,
                """
                SELECT *
                FROM jobs
                WHERE status IN ('pending','running')
                  AND created_at >= ? AND created_at < ?
                ORDER BY priority ASC, created_at ASC, job_id ASC
                LIMIT 5
                """,
                (start, end),
            )

        evidence_count = int(evidence_stats["evidence_count"] or 0)
        new_file_count = int(evidence_stats["new_file_count"] or 0)
        version_count = int(parse_stats["version_count"] or 0)
        parsed_version_count = int(parse_stats["parsed_version_count"] or 0)
        parse_pending_count = max(version_count - parsed_version_count - parse_failed_count, 0)
        parse_success_rate = _rate(
            parsed_version_count,
            parsed_version_count + parse_failed_count,
        )
        enhancement_job_count = int(enhancement_stats["job_count"] or 0)
        enhancement_succeeded_count = int(enhancement_stats["succeeded_count"] or 0)
        enhancement_failed_count = int(enhancement_stats["failed_count"] or 0)
        enhancement_pending_count = int(enhancement_stats["pending_count"] or 0)
        enhancement_success_rate = _rate(enhancement_succeeded_count, enhancement_job_count)
        unenhanced_evidence_count = max(evidence_count - enhanced_evidence_count, 0)
        recommendations = _recommendations(
            target_date=target_date,
            evidence_count=evidence_count,
            parse_failed_count=parse_failed_count,
            parse_pending_count=parse_pending_count,
            enhancement_job_count=enhancement_job_count,
            enhancement_failed_count=enhancement_failed_count,
            enhancement_pending_count=enhancement_pending_count,
            unenhanced_evidence_count=unenhanced_evidence_count,
            policy_blocked_count=policy_blocked_count,
            failed_jobs=failed_jobs,
            pending_jobs=pending_jobs,
        )
        severity = _severity(
            parse_failed_count=parse_failed_count,
            enhancement_failed_count=enhancement_failed_count,
            policy_blocked_count=policy_blocked_count,
            pending_job_count=len(pending_jobs),
        )

        return DataHealthSnapshot(
            report_date=target_date,
            new_file_count=new_file_count,
            evidence_count=evidence_count,
            parsed_version_count=parsed_version_count,
            parse_failed_count=parse_failed_count,
            parse_pending_count=parse_pending_count,
            parse_success_rate=parse_success_rate,
            enhancement_job_count=enhancement_job_count,
            enhancement_succeeded_count=enhancement_succeeded_count,
            enhancement_failed_count=enhancement_failed_count,
            enhancement_pending_count=enhancement_pending_count,
            enhancement_success_rate=enhancement_success_rate,
            enhanced_evidence_count=enhanced_evidence_count,
            unenhanced_evidence_count=unenhanced_evidence_count,
            policy_blocked_count=policy_blocked_count,
            failed_jobs=failed_jobs,
            pending_jobs=pending_jobs,
            recommendations=recommendations,
            severity=severity,
        )


def data_health_report_item(snapshot: DataHealthSnapshot | Mapping[str, Any]) -> dict[str, Any]:
    metrics = snapshot.to_dict() if isinstance(snapshot, DataHealthSnapshot) else dict(snapshot)
    return {
        "item_type": "data_health",
        "title": _title(metrics),
        "body": _body(metrics),
        "severity": metrics["severity"],
        "confidence": 1.0,
        "inferred": False,
        "evidence_ids": [],
        "metadata": {
            "metrics": metrics,
            "system_reference": "data_health",
        },
    }


def _title(metrics: Mapping[str, Any]) -> str:
    if int(metrics["evidence_count"]) == 0:
        return "Data Health: no evidence captured"
    return (
        "Data Health: "
        f"{metrics['new_file_count']} file(s), "
        f"{_percent(metrics['parse_success_rate'])} parse success, "
        f"{_percent(metrics['enhancement_success_rate'])} enhancement success"
    )


def _body(metrics: Mapping[str, Any]) -> str:
    lines = [
        f"New files: {metrics['new_file_count']}",
        f"Evidence items: {metrics['evidence_count']}",
        (
            "Parse: "
            f"{metrics['parsed_version_count']} succeeded, "
            f"{metrics['parse_failed_count']} failed, "
            f"{metrics['parse_pending_count']} pending "
            f"({_percent(metrics['parse_success_rate'])})"
        ),
        (
            "Enhancement jobs: "
            f"{metrics['enhancement_succeeded_count']} succeeded, "
            f"{metrics['enhancement_failed_count']} failed/blocked, "
            f"{metrics['enhancement_pending_count']} pending "
            f"({_percent(metrics['enhancement_success_rate'])})"
        ),
        (
            "Evidence enhancement coverage: "
            f"{metrics['enhanced_evidence_count']} enhanced, "
            f"{metrics['unenhanced_evidence_count']} not yet enhanced"
        ),
        f"Privacy policy blocks: {metrics['policy_blocked_count']}",
        f"Failed/blocked jobs: {len(metrics['failed_jobs'])}",
        f"Pending/running jobs: {len(metrics['pending_jobs'])}",
        "",
        "Recommendations:",
    ]
    lines.extend(f"- {item}" for item in metrics["recommendations"])
    return "\n".join(lines)


def _recommendations(
    *,
    target_date: str,
    evidence_count: int,
    parse_failed_count: int,
    parse_pending_count: int,
    enhancement_job_count: int,
    enhancement_failed_count: int,
    enhancement_pending_count: int,
    unenhanced_evidence_count: int,
    policy_blocked_count: int,
    failed_jobs: Sequence[Mapping[str, Any]],
    pending_jobs: Sequence[Mapping[str, Any]],
) -> list[str]:
    recommendations: list[str] = []
    if evidence_count == 0:
        recommendations.append("Add a filesystem source and run ego scan <source_id>.")
    if parse_failed_count:
        recommendations.append(
            "Review failed document_parse jobs; unsupported file types may need parser support or exclusion rules."
        )
    if parse_pending_count:
        recommendations.append("Run ego scan <source_id> again to process unparsed versions.")
    if enhancement_job_count == 0 and evidence_count:
        recommendations.append(f"Run ego enhance --date {target_date} --type tag.")
    if unenhanced_evidence_count:
        recommendations.append(
            f"Enhance {unenhanced_evidence_count} evidence item(s) before relying on tags or summaries."
        )
    if enhancement_failed_count:
        recommendations.append("Review failed enhancement jobs and retry after fixing the error.")
    if enhancement_pending_count or pending_jobs:
        recommendations.append("Run a Night Shift worker or CLI command to process pending jobs.")
    if policy_blocked_count:
        recommendations.append(
            "Keep sensitive data on local adapters or explicitly authorize external calls when appropriate."
        )
    if failed_jobs:
        recommendations.append("Use audit tail and job error messages to decide which failures are retryable.")
    if not recommendations:
        recommendations.append("No immediate action needed.")
    return recommendations


def _severity(
    *,
    parse_failed_count: int,
    enhancement_failed_count: int,
    policy_blocked_count: int,
    pending_job_count: int,
) -> str:
    if parse_failed_count or enhancement_failed_count:
        return "high"
    if policy_blocked_count:
        return "medium"
    if pending_job_count:
        return "low"
    return "info"


def _fetch_one_dict(connection, sql: str, params: Sequence[Any]) -> dict[str, Any]:
    return dict(connection.execute(sql, params).fetchone())


def _fetch_job_dicts(connection, sql: str, params: Sequence[Any]) -> list[dict[str, Any]]:
    rows = connection.execute(sql, params).fetchall()
    return [
        {
            "job_id": row["job_id"],
            "job_type": row["job_type"],
            "status": row["status"],
            "error_message": row["error_message"],
            "retry_count": row["retry_count"],
            "max_retries": row["max_retries"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.0f}%"


def _normalize_date(value: str) -> str:
    return normalize_report_date(value)


def _date_bounds(value: str) -> tuple[str, str]:
    return local_date_bounds_as_utc(value)
