"""Operator Bridge dry-run action planning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ego_data_core.audit import append_audit_log
from ego_data_core.kernel.id_generator import generate_id
from ego_data_core.storage.db import get_connection, run_migrations, transaction
from ego_data_core.workgraph import AutomationOpportunityService


@dataclass(frozen=True)
class ActionPlanRecord:
    action_id: str
    project_id: str | None
    title: str
    goal: str | None
    risk_level: str
    status: str
    requires_authorization: bool
    plan: dict[str, Any]
    metadata: dict[str, Any]
    steps: list[dict[str, Any]]
    created_at: str
    updated_at: str


class OperatorBridge:
    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = database_path

    def propose_action(self, automation_id: str) -> dict[str, Any]:
        run_migrations(self.database_path)
        opportunity = AutomationOpportunityService(self.database_path).get_opportunity(
            automation_id
        )
        existing = self._find_existing_action(automation_id)
        if existing:
            record = self.get_action(existing)
            append_audit_log(
                "action_proposed",
                actor="operator",
                target={"type": "action", "id": record.action_id},
                payload={
                    "automation_id": automation_id,
                    "reused": True,
                    "dry_run_only": True,
                },
                database_path=self.database_path,
            )
            return action_plan_to_dict(record)

        now = _utc_now()
        action_id = generate_id("act")
        plan = _build_plan(opportunity)
        metadata = {
            "automation_id": automation_id,
            "dry_run_only": True,
            "operator_bridge_version": "v0.1",
            "required_authorization": opportunity.metadata.get(
                "required_authorization"
            ),
            "evidence_ids": opportunity.evidence_ids,
        }
        steps = _build_steps(opportunity, plan)

        with get_connection(self.database_path) as connection:
            with transaction(connection):
                connection.execute(
                    """
                    INSERT INTO actions(
                      action_id,
                      project_id,
                      title,
                      goal,
                      risk_level,
                      status,
                      requires_authorization,
                      plan_json,
                      created_at,
                      updated_at,
                      metadata_json
                    )
                    VALUES (?, ?, ?, ?, ?, 'proposed', ?, ?, ?, ?, ?)
                    """,
                    (
                        action_id,
                        opportunity.project_id,
                        f"Dry-run: {opportunity.title}",
                        opportunity.description,
                        opportunity.risk_level,
                        int(opportunity.requires_authorization),
                        _to_json(plan),
                        now,
                        now,
                        _to_json(metadata),
                    ),
                )
                for index, step in enumerate(steps, start=1):
                    connection.execute(
                        """
                        INSERT INTO action_steps(
                          action_step_id,
                          action_id,
                          step_order,
                          step_type,
                          description,
                          status,
                          input_json,
                          output_json,
                          created_at,
                          updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, 'pending', ?, '{}', ?, ?)
                        """,
                        (
                            generate_id("item"),
                            action_id,
                            index,
                            step["step_type"],
                            step["description"],
                            _to_json(step.get("input") or {}),
                            now,
                            now,
                        ),
                    )

        append_audit_log(
            "action_proposed",
            actor="operator",
            target={"type": "action", "id": action_id},
            payload={
                "automation_id": automation_id,
                "risk_level": opportunity.risk_level,
                "requires_authorization": opportunity.requires_authorization,
                "dry_run_only": True,
            },
            database_path=self.database_path,
        )
        return action_plan_to_dict(self.get_action(action_id))

    def authorize_action(
        self,
        action_id: str,
        *,
        user_id: str | None = None,
        authorization_type: str = "one_time",
    ) -> dict[str, Any]:
        record = self.get_action(action_id)
        now = _utc_now()
        normalized_type = _normalize_authorization_type(authorization_type)

        with get_connection(self.database_path) as connection:
            local_user_id = user_id or _ensure_local_user(connection, now)
            authorization_id = generate_id("act")
            with transaction(connection):
                connection.execute(
                    """
                    INSERT INTO authorizations(
                      authorization_id,
                      action_id,
                      user_id,
                      authorization_type,
                      scope_json,
                      status,
                      granted_at
                    )
                    VALUES (?, ?, ?, ?, ?, 'active', ?)
                    """,
                    (
                        authorization_id,
                        action_id,
                        local_user_id,
                        normalized_type,
                        _to_json(
                            {
                                "dry_run_only": True,
                                "risk_level": record.risk_level,
                                "action_id": action_id,
                            }
                        ),
                        now,
                    ),
                )
                connection.execute(
                    """
                    UPDATE actions
                    SET status = 'authorized',
                        updated_at = ?
                    WHERE action_id = ?
                    """,
                    (now, action_id),
                )

        append_audit_log(
            "action_authorized",
            actor={"type": "user", "id": local_user_id},
            target={"type": "action", "id": action_id},
            payload={
                "authorization_id": authorization_id,
                "authorization_type": normalized_type,
                "dry_run_only": True,
            },
            database_path=self.database_path,
        )
        payload = action_plan_to_dict(self.get_action(action_id))
        payload["authorization_id"] = authorization_id
        return payload

    def execute_action(self, action_id: str, *, dry_run: bool = True) -> dict[str, Any]:
        record = self.get_action(action_id)
        if not dry_run:
            raise ValueError("Operator Bridge v0.1 only supports dry_run execution")

        if record.requires_authorization and not self._has_active_authorization(action_id):
            append_audit_log(
                "action_execute_blocked",
                actor="operator",
                target={"type": "action", "id": action_id},
                payload={
                    "reason": "requires_authorization",
                    "dry_run_only": True,
                },
                database_path=self.database_path,
            )
            return {
                "action_id": action_id,
                "status": "requires_authorization",
                "requires_authorization": True,
                "dry_run": True,
                "risk_level": record.risk_level,
                "risk_explanation": record.plan.get("risk_explanation"),
                "dry_run_steps": record.plan.get("dry_run_steps") or [],
            }

        now = _utc_now()
        dry_run_steps = record.plan.get("dry_run_steps") or []
        with get_connection(self.database_path) as connection:
            with transaction(connection):
                connection.execute(
                    """
                    UPDATE actions
                    SET status = 'succeeded',
                        updated_at = ?
                    WHERE action_id = ?
                    """,
                    (now, action_id),
                )
                for step in record.steps:
                    connection.execute(
                        """
                        UPDATE action_steps
                        SET status = 'skipped',
                            output_json = ?,
                            updated_at = ?
                        WHERE action_step_id = ?
                        """,
                        (
                            _to_json(
                                {
                                    "dry_run_only": True,
                                    "simulated": True,
                                    "message": "No computer action was executed.",
                                }
                            ),
                            now,
                            step["action_step_id"],
                        ),
                    )

        append_audit_log(
            "action_executed",
            actor="operator",
            target={"type": "action", "id": action_id},
            payload={
                "dry_run_only": True,
                "step_count": len(dry_run_steps),
                "risk_level": record.risk_level,
            },
            database_path=self.database_path,
        )
        return {
            "action_id": action_id,
            "status": "dry_run_completed",
            "requires_authorization": record.requires_authorization,
            "dry_run": True,
            "risk_level": record.risk_level,
            "risk_explanation": record.plan.get("risk_explanation"),
            "dry_run_steps": dry_run_steps,
            "action": action_plan_to_dict(self.get_action(action_id)),
        }

    def get_action(self, action_id: str) -> ActionPlanRecord:
        run_migrations(self.database_path)
        with get_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM actions WHERE action_id = ?",
                (action_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Action not found: {action_id}")
            step_rows = connection.execute(
                """
                SELECT *
                FROM action_steps
                WHERE action_id = ?
                ORDER BY step_order ASC
                """,
                (action_id,),
            ).fetchall()
        return _row_to_action(row, step_rows)

    def _find_existing_action(self, automation_id: str) -> str | None:
        with get_connection(self.database_path) as connection:
            rows = connection.execute(
                "SELECT action_id, metadata_json FROM actions"
            ).fetchall()
        for row in rows:
            metadata = json.loads(row["metadata_json"])
            if metadata.get("automation_id") == automation_id:
                return row["action_id"]
        return None

    def _has_active_authorization(self, action_id: str) -> bool:
        with get_connection(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT authorization_id
                FROM authorizations
                WHERE action_id = ?
                  AND status = 'active'
                ORDER BY granted_at DESC
                LIMIT 1
                """,
                (action_id,),
            ).fetchone()
        return row is not None


def action_plan_to_dict(record: ActionPlanRecord) -> dict[str, Any]:
    return {
        "action_id": record.action_id,
        "project_id": record.project_id,
        "title": record.title,
        "goal": record.goal,
        "risk_level": record.risk_level,
        "status": record.status,
        "requires_authorization": record.requires_authorization,
        "plan": record.plan,
        "metadata": record.metadata,
        "steps": record.steps,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def _build_plan(opportunity) -> dict[str, Any]:
    dry_run_steps = _dry_run_steps(opportunity.pattern)
    return {
        "dry_run_only": True,
        "automation_id": opportunity.automation_id,
        "suggested_action": opportunity.metadata.get("suggested_action"),
        "required_authorization": opportunity.metadata.get("required_authorization"),
        "risk_level": opportunity.risk_level,
        "risk_explanation": opportunity.metadata.get("risk_reason")
        or "This action plan is generated as a dry-run only.",
        "evidence_ids": opportunity.evidence_ids,
        "pattern": opportunity.pattern,
        "dry_run_steps": dry_run_steps,
    }


def _build_steps(opportunity, plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "step_type": "review_evidence",
            "description": "Review linked evidence and confirm this opportunity is valid.",
            "input": {"evidence_ids": opportunity.evidence_ids},
        },
        {
            "step_type": "risk_review",
            "description": "Review risk level and required authorization before any action.",
            "input": {
                "risk_level": opportunity.risk_level,
                "required_authorization": opportunity.metadata.get(
                    "required_authorization"
                ),
            },
        },
        {
            "step_type": "prepare_manual_plan",
            "description": "Prepare a manual checklist or script draft without running it.",
            "input": {"dry_run_steps": plan.get("dry_run_steps") or []},
        },
        {
            "step_type": "no_operation",
            "description": "Stop before controlling the computer or changing files.",
            "input": {"dry_run_only": True},
        },
    ]


def _dry_run_steps(pattern: Mapping[str, Any]) -> list[str]:
    pattern_type = pattern.get("pattern_type")
    if pattern_type == "duplicate_files":
        titles = pattern.get("titles") or []
        return [
            "List duplicate candidates by title and content hash.",
            "Ask the user to choose the canonical file before cleanup.",
            f"Prepare a non-executed cleanup checklist for {len(titles)} file(s).",
            "Do not delete or move any file in v0.1 dry-run.",
        ]
    if pattern_type == "loose_folder":
        folder = pattern.get("folder") or "loose folder"
        return [
            f"List evidence items currently in {folder}.",
            "Group files by likely project or topic.",
            "Prepare a review queue before any move action.",
            "Do not move files in v0.1 dry-run.",
        ]
    if pattern_type == "dispersed_project_files":
        return [
            "List folders that contain evidence for the same project.",
            "Draft a project organization proposal.",
            "Ask for explicit authorization before moving anything.",
            "Do not move files in v0.1 dry-run.",
        ]
    return [
        "Review the automation opportunity.",
        "Draft a safe manual plan.",
        "Stop before any real-world execution.",
    ]


def _row_to_action(row, step_rows: Sequence[Any]) -> ActionPlanRecord:
    return ActionPlanRecord(
        action_id=row["action_id"],
        project_id=row["project_id"],
        title=row["title"],
        goal=row["goal"],
        risk_level=row["risk_level"],
        status=row["status"],
        requires_authorization=bool(row["requires_authorization"]),
        plan=json.loads(row["plan_json"]),
        metadata=json.loads(row["metadata_json"]),
        steps=[_row_to_step(step) for step in step_rows],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_step(row) -> dict[str, Any]:
    return {
        "action_step_id": row["action_step_id"],
        "action_id": row["action_id"],
        "step_order": row["step_order"],
        "step_type": row["step_type"],
        "description": row["description"],
        "status": row["status"],
        "input": json.loads(row["input_json"]),
        "output": json.loads(row["output_json"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _ensure_local_user(connection, now: str) -> str:
    row = connection.execute(
        "SELECT user_id FROM users ORDER BY created_at ASC LIMIT 1"
    ).fetchone()
    if row:
        return row["user_id"]
    user_id = generate_id("usr")
    connection.execute(
        """
        INSERT INTO users(user_id, display_name, created_at, updated_at)
        VALUES (?, 'Local Ego User', ?, ?)
        """,
        (user_id, now, now),
    )
    return user_id


def _normalize_authorization_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"one_time", "session", "policy"}:
        raise ValueError("authorization_type must be one_time, session, or policy")
    return normalized


def _to_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
