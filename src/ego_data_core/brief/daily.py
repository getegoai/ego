"""Daily Brief generator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ego_data_core.audit import append_audit_log
from ego_data_core.brief.data_health import DataHealthService, data_health_report_item
from ego_data_core.brief.export_markdown import BriefMarkdownExporter
from ego_data_core.kernel.id_generator import generate_id
from ego_data_core.storage.db import get_connection, run_migrations, transaction
from ego_data_core.vault import VaultStorage


REPORT_FEEDBACK = frozenset(
    {"confirm", "reject", "edit", "later", "convert_to_task", "authorize_action"}
)


@dataclass(frozen=True)
class DailyBriefRecord:
    report_id: str
    report_type: str
    title: str
    report_date: str
    status: str
    summary: str | None
    generated_at: str
    metadata: dict[str, Any]
    items: list[dict[str, Any]]
    created_at: str
    updated_at: str


class DailyBriefService:
    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        storage: VaultStorage | None = None,
    ) -> None:
        self.database_path = database_path
        self.storage = storage or VaultStorage()

    def generate_daily_brief(
        self,
        report_date: str | None = None,
        *,
        force_regenerate: bool = False,
    ) -> DailyBriefRecord:
        run_migrations(self.database_path)
        target_date = _normalize_date(report_date)
        existing = self._latest_report_for_date(target_date)
        if existing and not force_regenerate:
            return existing
        if existing and force_regenerate:
            self._archive_report(existing.report_id)

        context = self._load_context(target_date)
        now = _utc_now()
        report_id = generate_id("report")
        title = f"Ego Daily Brief - {target_date}"
        items = _build_report_items(context)
        summary = _brief_summary(context, items)
        metadata = {
            "evidence_count": len(context["evidence"]),
            "enhancement_count": len(context["enhancements"]),
            "project_count": len(context["projects"]),
            "task_count": len(context["tasks"]),
            "question_count": len(context["questions"]),
            "risk_count": len(context["risks"]),
            "data_health": context["data_health"],
        }

        with get_connection(self.database_path) as connection:
            with transaction(connection):
                connection.execute(
                    """
                    INSERT INTO reports(
                      report_id,
                      report_type,
                      title,
                      report_date,
                      status,
                      summary,
                      generated_at,
                      metadata_json,
                      created_at,
                      updated_at
                    )
                    VALUES (?, 'daily', ?, ?, 'published', ?, ?, ?, ?, ?)
                    """,
                    (
                        report_id,
                        title,
                        target_date,
                        summary,
                        now,
                        _to_json(metadata),
                        now,
                        now,
                    ),
                )
                for order, item in enumerate(items):
                    item_id = generate_id("item")
                    item["report_item_id"] = item_id
                    connection.execute(
                        """
                        INSERT INTO report_items(
                          report_item_id,
                          report_id,
                          item_order,
                          item_type,
                          title,
                          body,
                          severity,
                          confidence,
                          inferred,
                          created_at,
                          updated_at,
                          metadata_json
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item_id,
                            report_id,
                            order,
                            item["item_type"],
                            item["title"],
                            item.get("body"),
                            item.get("severity", "info"),
                            item.get("confidence"),
                            int(bool(item.get("inferred", False))),
                            now,
                            now,
                            _to_json(item.get("metadata") or {}),
                        ),
                    )
                    for evidence_id in item.get("evidence_ids") or []:
                        connection.execute(
                            """
                            INSERT OR IGNORE INTO report_item_evidence_links(
                              report_item_id,
                              evidence_id,
                              note,
                              created_at
                            )
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                item_id,
                                evidence_id,
                                item.get("evidence_note") or item["item_type"],
                                now,
                            ),
                        )

        markdown_uri = self._export_markdown(report_id)
        self._update_report_metadata(report_id, {"markdown_uri": markdown_uri})
        append_audit_log(
            "brief_generated",
            actor="system",
            target={"type": "report", "id": report_id},
            payload={
                "report_type": "daily",
                "report_date": target_date,
                "item_count": len(items),
                "markdown_uri": markdown_uri,
            },
            database_path=self.database_path,
        )
        return self.get_report(report_id)

    def get_latest_daily_brief(self) -> DailyBriefRecord | None:
        run_migrations(self.database_path)
        with get_connection(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT report_id
                FROM reports
                WHERE report_type = 'daily'
                  AND status = 'published'
                ORDER BY generated_at DESC, report_id DESC
                LIMIT 1
                """
            ).fetchone()
        return self.get_report(row["report_id"]) if row else None

    def get_report(self, report_id: str) -> DailyBriefRecord:
        run_migrations(self.database_path)
        with get_connection(self.database_path) as connection:
            report = connection.execute(
                "SELECT * FROM reports WHERE report_id = ?",
                (report_id,),
            ).fetchone()
            if report is None:
                raise ValueError(f"Report not found: {report_id}")
            item_rows = connection.execute(
                """
                SELECT *
                FROM report_items
                WHERE report_id = ?
                ORDER BY item_order ASC
                """,
                (report_id,),
            ).fetchall()
            link_rows = connection.execute(
                """
                SELECT report_item_id, evidence_id
                FROM report_item_evidence_links
                WHERE report_item_id IN (
                  SELECT report_item_id FROM report_items WHERE report_id = ?
                )
                ORDER BY report_item_id, evidence_id
                """,
                (report_id,),
            ).fetchall()

        evidence_by_item: dict[str, list[str]] = {}
        for row in link_rows:
            evidence_by_item.setdefault(row["report_item_id"], []).append(row["evidence_id"])
        return _row_to_report(report, item_rows, evidence_by_item)

    def apply_item_feedback(
        self,
        report_item_id: str,
        feedback: str,
    ) -> dict[str, Any]:
        normalized = feedback.strip().lower()
        if normalized not in REPORT_FEEDBACK:
            allowed = ", ".join(sorted(REPORT_FEEDBACK))
            raise ValueError(f"Unsupported report item feedback '{feedback}'. Allowed: {allowed}")
        now = _utc_now()
        run_migrations(self.database_path)
        with get_connection(self.database_path) as connection:
            connection.execute(
                """
                UPDATE report_items
                SET user_feedback = ?,
                    updated_at = ?
                WHERE report_item_id = ?
                """,
                (normalized, now, report_item_id),
            )
            connection.commit()
            row = connection.execute(
                "SELECT * FROM report_items WHERE report_item_id = ?",
                (report_item_id,),
            ).fetchone()
        if row is None:
            raise ValueError(f"Report item not found: {report_item_id}")
        return _report_item_to_dict(row, [])

    def _load_context(self, target_date: str) -> dict[str, Any]:
        start, end = _date_bounds(target_date)
        with get_connection(self.database_path) as connection:
            evidence = _fetch_all_dicts(
                connection,
                """
                SELECT
                  ev.evidence_id,
                  ev.captured_at,
                  raw.title,
                  raw.metadata_json AS raw_metadata_json
                FROM evidence ev
                JOIN raw_objects raw ON raw.raw_object_id = ev.raw_object_id
                WHERE ev.captured_at >= ? AND ev.captured_at < ?
                ORDER BY ev.captured_at ASC, ev.evidence_id ASC
                """,
                (start, end),
            )
            enhancements = _fetch_all_dicts(
                connection,
                """
                SELECT enh.*, link.evidence_id
                FROM enhancements enh
                JOIN enhancement_evidence_links link
                  ON link.enhancement_id = enh.enhancement_id
                WHERE enh.generated_at >= ? AND enh.generated_at < ?
                ORDER BY enh.generated_at ASC, enh.enhancement_id ASC
                """,
                (start, end),
            )
            projects = _fetch_all_dicts(
                connection,
                """
                SELECT *
                FROM projects
                WHERE updated_at >= ? AND updated_at < ?
                ORDER BY updated_at ASC, project_id ASC
                """,
                (start, end),
            )
            tasks = _fetch_all_dicts(
                connection,
                """
                SELECT *
                FROM tasks
                WHERE created_at >= ? AND created_at < ?
                ORDER BY created_at ASC, task_id ASC
                """,
                (start, end),
            )
            questions = _fetch_all_dicts(
                connection,
                """
                SELECT *
                FROM questions
                WHERE created_at >= ? AND created_at < ?
                ORDER BY created_at ASC, question_id ASC
                """,
                (start, end),
            )
            risks = _fetch_all_dicts(
                connection,
                """
                SELECT *
                FROM risks
                WHERE created_at >= ? AND created_at < ?
                ORDER BY created_at ASC, risk_id ASC
                """,
                (start, end),
            )
            evidence_by_item = _evidence_by_work_item(connection)
            evidence_by_project = _evidence_by_project(connection)

        for row in evidence:
            row["metadata"] = json.loads(row.pop("raw_metadata_json"))
        for row in enhancements:
            row["content"] = json.loads(row.pop("content_json"))
            row["metadata"] = json.loads(row.pop("metadata_json"))
        for row in projects:
            row["metadata"] = json.loads(row.pop("metadata_json"))
            row["evidence_ids"] = evidence_by_project.get(row["project_id"], [])
        for item_type, rows in (("task", tasks), ("question", questions), ("risk", risks)):
            id_key = f"{item_type}_id" if item_type != "question" else "question_id"
            for row in rows:
                row["metadata"] = json.loads(row.pop("metadata_json"))
                row["evidence_ids"] = evidence_by_item.get((item_type, row[id_key]), [])
        return {
            "evidence": evidence,
            "enhancements": enhancements,
            "projects": projects,
            "tasks": tasks,
            "questions": questions,
            "risks": risks,
            "data_health": DataHealthService(self.database_path).snapshot(target_date).to_dict(),
        }

    def _latest_report_for_date(self, target_date: str) -> DailyBriefRecord | None:
        with get_connection(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT report_id
                FROM reports
                WHERE report_type = 'daily'
                  AND report_date = ?
                  AND status = 'published'
                ORDER BY generated_at DESC, report_id DESC
                LIMIT 1
                """,
                (target_date,),
            ).fetchone()
        return self.get_report(row["report_id"]) if row else None

    def _archive_report(self, report_id: str) -> None:
        with get_connection(self.database_path) as connection:
            connection.execute(
                """
                UPDATE reports
                SET status = 'archived',
                    updated_at = ?
                WHERE report_id = ?
                """,
                (_utc_now(), report_id),
            )
            connection.commit()

    def _export_markdown(self, report_id: str) -> str:
        report = self.get_report(report_id)
        return BriefMarkdownExporter(
            self.database_path,
            storage=self.storage,
        ).export_report(report)

    def _update_report_metadata(self, report_id: str, patch: Mapping[str, Any]) -> None:
        with get_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT metadata_json FROM reports WHERE report_id = ?",
                (report_id,),
            ).fetchone()
            metadata = json.loads(row["metadata_json"]) if row else {}
            metadata.update(dict(patch))
            connection.execute(
                """
                UPDATE reports
                SET metadata_json = ?,
                    updated_at = ?
                WHERE report_id = ?
                """,
                (_to_json(metadata), _utc_now(), report_id),
            )
            connection.commit()


def daily_brief_to_dict(record: DailyBriefRecord) -> dict[str, Any]:
    return {
        "report_id": record.report_id,
        "report_type": record.report_type,
        "title": record.title,
        "report_date": record.report_date,
        "status": record.status,
        "summary": record.summary,
        "generated_at": record.generated_at,
        "metadata": record.metadata,
        "items": record.items,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def _build_report_items(context: Mapping[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    evidence = context["evidence"]
    if evidence:
        items.append(
            {
                "item_type": "new_evidence",
                "title": f"{len(evidence)} new evidence item(s)",
                "body": ", ".join(item["title"] for item in evidence[:5]),
                "severity": "info",
                "confidence": 1.0,
                "inferred": False,
                "evidence_ids": [item["evidence_id"] for item in evidence],
            }
        )

    for project in context["projects"]:
        evidence_ids = project.get("evidence_ids") or []
        if not evidence_ids:
            continue
        items.append(
            {
                "item_type": "project_update",
                "title": f"Project candidate: {project['name']}",
                "body": project.get("summary"),
                "severity": "info",
                "confidence": project.get("confidence"),
                "inferred": True,
                "evidence_ids": evidence_ids,
            }
        )

    for task in context["tasks"]:
        items.append(_work_item_report_item("task", task))
    for question in context["questions"]:
        items.append(_work_item_report_item("question", question))
    for risk in context["risks"]:
        item = _work_item_report_item("risk", risk)
        item["severity"] = "medium"
        items.append(item)

    items.append(data_health_report_item(context["data_health"]))

    return items


def _work_item_report_item(item_type: str, row: Mapping[str, Any]) -> dict[str, Any]:
    body = row.get("description") or row.get("body")
    return {
        "item_type": item_type,
        "title": row["title"],
        "body": body,
        "severity": "info",
        "confidence": row.get("confidence"),
        "inferred": True,
        "evidence_ids": row.get("evidence_ids") or [],
        "metadata": {
            f"{item_type}_id": row[f"{item_type}_id"],
            "project_id": row.get("project_id"),
        },
    }


def _brief_summary(
    context: Mapping[str, Any],
    items: Sequence[Mapping[str, Any]],
) -> str:
    return (
        f"{len(context['evidence'])} evidence item(s), "
        f"{len(context['projects'])} project update(s), "
        f"{len(context['tasks'])} task(s), "
        f"{len(context['questions'])} question(s), "
        f"{len(context['risks'])} risk(s), "
        f"{len(items)} brief item(s)."
    )


def _row_to_report(row, item_rows, evidence_by_item: Mapping[str, list[str]]) -> DailyBriefRecord:
    return DailyBriefRecord(
        report_id=row["report_id"],
        report_type=row["report_type"],
        title=row["title"],
        report_date=row["report_date"],
        status=row["status"],
        summary=row["summary"],
        generated_at=row["generated_at"],
        metadata=json.loads(row["metadata_json"]),
        items=[
            _report_item_to_dict(item, evidence_by_item.get(item["report_item_id"], []))
            for item in item_rows
        ],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _report_item_to_dict(row, evidence_ids: list[str]) -> dict[str, Any]:
    return {
        "report_item_id": row["report_item_id"],
        "report_id": row["report_id"],
        "item_order": row["item_order"],
        "item_type": row["item_type"],
        "title": row["title"],
        "body": row["body"],
        "severity": row["severity"],
        "confidence": row["confidence"],
        "inferred": bool(row["inferred"]),
        "user_feedback": row["user_feedback"],
        "metadata": json.loads(row["metadata_json"]),
        "evidence_ids": evidence_ids,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _fetch_all_dicts(connection, sql: str, params: Sequence[Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in connection.execute(sql, params).fetchall()]


def _evidence_by_work_item(connection) -> dict[tuple[str, str], list[str]]:
    rows = connection.execute(
        """
        SELECT dst_type, dst_id, evidence_id
        FROM graph_edges
        WHERE dst_type IN ('task', 'question', 'risk')
          AND evidence_id IS NOT NULL
        ORDER BY dst_type, dst_id, evidence_id
        """
    ).fetchall()
    result: dict[tuple[str, str], list[str]] = {}
    for row in rows:
        result.setdefault((row["dst_type"], row["dst_id"]), []).append(row["evidence_id"])
    return result


def _evidence_by_project(connection) -> dict[str, list[str]]:
    rows = connection.execute(
        """
        SELECT project_id, subject_id AS evidence_id
        FROM project_links
        WHERE subject_type = 'evidence'
        ORDER BY project_id, subject_id
        """
    ).fetchall()
    result: dict[str, list[str]] = {}
    for row in rows:
        result.setdefault(row["project_id"], []).append(row["evidence_id"])
    return result


def _normalize_date(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).date().isoformat()
    return date.fromisoformat(value).isoformat()


def _date_bounds(value: str) -> tuple[str, str]:
    start_date = date.fromisoformat(value)
    end_date = start_date + timedelta(days=1)
    return (
        datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc).isoformat(),
        datetime.combine(end_date, datetime.min.time(), tzinfo=timezone.utc).isoformat(),
    )


def _to_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
