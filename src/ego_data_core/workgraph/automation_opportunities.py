"""Rule-based automation opportunity discovery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ego_data_core.kernel.id_generator import generate_id
from ego_data_core.storage.db import get_connection, run_migrations, transaction


HIGH_RISK_ACTIONS = frozenset({"move", "delete", "send", "upload"})


@dataclass(frozen=True)
class AutomationOpportunityRecord:
    automation_id: str
    project_id: str | None
    title: str
    description: str | None
    pattern: dict[str, Any]
    risk_level: str
    status: str
    requires_authorization: bool
    source_enhancement_id: str | None
    confidence: float | None
    metadata: dict[str, Any]
    evidence_ids: list[str]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class _RawObjectContext:
    raw_object_id: str
    source_id: str
    title: str
    content_hash: str | None
    size_bytes: int | None
    relative_path: str
    captured_at: str | None
    modified_at: str | None
    evidence_ids: list[str]
    project_ids: list[str]


@dataclass(frozen=True)
class _OpportunityCandidate:
    discovery_key: str
    title: str
    description: str
    pattern: dict[str, Any]
    risk_level: str
    required_authorization: str
    confidence: float
    evidence_ids: list[str]
    project_id: str | None = None


class AutomationOpportunityService:
    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = database_path

    def discover_opportunities(self) -> dict[str, Any]:
        run_migrations(self.database_path)
        objects = self._load_raw_objects()
        candidates = [
            *_duplicate_file_candidates(objects),
            *_loose_folder_candidates(objects),
            *_dispersed_project_candidates(objects),
        ]

        created: list[AutomationOpportunityRecord] = []
        for candidate in candidates:
            created.append(self._upsert_candidate(candidate))

        return {
            "items": [automation_opportunity_to_dict(item) for item in created],
            "total": len(created),
        }

    def list_opportunities(self) -> dict[str, Any]:
        run_migrations(self.database_path)
        with get_connection(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM automations
                ORDER BY updated_at DESC, automation_id DESC
                """
            ).fetchall()
            evidence_by_automation = {
                row["automation_id"]: _evidence_for_automation(
                    connection,
                    row["automation_id"],
                )
                for row in rows
            }

        records = [
            _row_to_automation(row, evidence_by_automation[row["automation_id"]])
            for row in rows
        ]
        return {
            "items": [automation_opportunity_to_dict(record) for record in records],
            "total": len(records),
        }

    def get_opportunity(self, automation_id: str) -> AutomationOpportunityRecord:
        with get_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM automations WHERE automation_id = ?",
                (automation_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Automation opportunity not found: {automation_id}")
            evidence_ids = _evidence_for_automation(connection, automation_id)
        return _row_to_automation(row, evidence_ids)

    def _upsert_candidate(
        self,
        candidate: _OpportunityCandidate,
    ) -> AutomationOpportunityRecord:
        existing_id = self._find_existing(candidate.discovery_key)
        if existing_id:
            self._refresh_candidate(existing_id, candidate)
            return self.get_opportunity(existing_id)
        automation_id = self._insert_candidate(candidate)
        return self.get_opportunity(automation_id)

    def _find_existing(self, discovery_key: str) -> str | None:
        with get_connection(self.database_path) as connection:
            rows = connection.execute(
                "SELECT automation_id, metadata_json FROM automations"
            ).fetchall()
        for row in rows:
            metadata = json.loads(row["metadata_json"])
            if metadata.get("discovery_key") == discovery_key:
                return row["automation_id"]
        return None

    def _insert_candidate(self, candidate: _OpportunityCandidate) -> str:
        now = _utc_now()
        automation_id = generate_id("auto")
        risk_level = _effective_risk(candidate)
        requires_authorization = _requires_authorization(candidate, risk_level)
        metadata = _candidate_metadata(candidate, risk_level, requires_authorization)

        with get_connection(self.database_path) as connection:
            with transaction(connection):
                connection.execute(
                    """
                    INSERT INTO automations(
                      automation_id,
                      project_id,
                      title,
                      description,
                      pattern_json,
                      risk_level,
                      status,
                      requires_authorization,
                      source_enhancement_id,
                      confidence,
                      created_at,
                      updated_at,
                      metadata_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 'proposed', ?, NULL, ?, ?, ?, ?)
                    """,
                    (
                        automation_id,
                        candidate.project_id,
                        candidate.title,
                        candidate.description,
                        _to_json(candidate.pattern),
                        risk_level,
                        int(requires_authorization),
                        candidate.confidence,
                        now,
                        now,
                        _to_json(metadata),
                    ),
                )
                _replace_automation_links(
                    connection,
                    automation_id,
                    candidate.project_id,
                    candidate.evidence_ids,
                    candidate.confidence,
                    now,
                )
        return automation_id

    def _refresh_candidate(
        self,
        automation_id: str,
        candidate: _OpportunityCandidate,
    ) -> None:
        now = _utc_now()
        risk_level = _effective_risk(candidate)
        requires_authorization = _requires_authorization(candidate, risk_level)
        metadata = _candidate_metadata(candidate, risk_level, requires_authorization)
        with get_connection(self.database_path) as connection:
            with transaction(connection):
                connection.execute(
                    """
                    UPDATE automations
                    SET project_id = ?,
                        title = ?,
                        description = ?,
                        pattern_json = ?,
                        risk_level = ?,
                        requires_authorization = ?,
                        confidence = ?,
                        updated_at = ?,
                        metadata_json = ?
                    WHERE automation_id = ?
                    """,
                    (
                        candidate.project_id,
                        candidate.title,
                        candidate.description,
                        _to_json(candidate.pattern),
                        risk_level,
                        int(requires_authorization),
                        candidate.confidence,
                        now,
                        _to_json(metadata),
                        automation_id,
                    ),
                )
                _replace_automation_links(
                    connection,
                    automation_id,
                    candidate.project_id,
                    candidate.evidence_ids,
                    candidate.confidence,
                    now,
                )

    def _load_raw_objects(self) -> list[_RawObjectContext]:
        with get_connection(self.database_path) as connection:
            raw_rows = connection.execute(
                """
                SELECT
                  raw.raw_object_id,
                  raw.source_id,
                  raw.title,
                  raw.content_hash,
                  raw.size_bytes,
                  raw.captured_at,
                  raw.modified_at,
                  raw.metadata_json
                FROM raw_objects AS raw
                WHERE raw.status = 'active'
                ORDER BY raw.captured_at ASC, raw.raw_object_id ASC
                """
            ).fetchall()
            evidence_rows = connection.execute(
                """
                SELECT raw_object_id, evidence_id
                FROM evidence
                ORDER BY raw_object_id ASC, evidence_id ASC
                """
            ).fetchall()
            project_rows = connection.execute(
                """
                SELECT project_id, subject_id AS raw_object_id
                FROM project_links
                WHERE subject_type = 'raw_object'
                ORDER BY created_at ASC
                """
            ).fetchall()

        evidence_by_raw: dict[str, list[str]] = {}
        for row in evidence_rows:
            evidence_by_raw.setdefault(row["raw_object_id"], []).append(row["evidence_id"])

        projects_by_raw: dict[str, list[str]] = {}
        for row in project_rows:
            projects_by_raw.setdefault(row["raw_object_id"], []).append(row["project_id"])

        objects: list[_RawObjectContext] = []
        for row in raw_rows:
            metadata = json.loads(row["metadata_json"])
            relative_path = metadata.get("relative_path") or row["title"] or row["raw_object_id"]
            objects.append(
                _RawObjectContext(
                    raw_object_id=row["raw_object_id"],
                    source_id=row["source_id"],
                    title=row["title"] or "Untitled",
                    content_hash=row["content_hash"],
                    size_bytes=row["size_bytes"],
                    relative_path=relative_path,
                    captured_at=row["captured_at"],
                    modified_at=row["modified_at"],
                    evidence_ids=evidence_by_raw.get(row["raw_object_id"], []),
                    project_ids=projects_by_raw.get(row["raw_object_id"], []),
                )
            )
        return objects


def automation_opportunity_to_dict(
    record: AutomationOpportunityRecord,
) -> dict[str, Any]:
    return {
        "automation_id": record.automation_id,
        "project_id": record.project_id,
        "title": record.title,
        "description": record.description,
        "pattern": record.pattern,
        "risk_level": record.risk_level,
        "status": record.status,
        "requires_authorization": record.requires_authorization,
        "required_authorization": record.metadata.get("required_authorization"),
        "suggested_action": record.metadata.get("suggested_action"),
        "source_enhancement_id": record.source_enhancement_id,
        "confidence": record.confidence,
        "metadata": record.metadata,
        "evidence_ids": record.evidence_ids,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def _duplicate_file_candidates(
    objects: Sequence[_RawObjectContext],
) -> list[_OpportunityCandidate]:
    grouped: dict[str, list[_RawObjectContext]] = {}
    for item in objects:
        if item.content_hash and item.evidence_ids:
            grouped.setdefault(item.content_hash, []).append(item)

    candidates: list[_OpportunityCandidate] = []
    for content_hash, items in grouped.items():
        if len(items) < 2:
            continue
        title = f"Review {len(items)} duplicate file candidates"
        evidence_ids = _evidence_ids(items)
        candidates.append(
            _OpportunityCandidate(
                discovery_key=f"duplicate:{content_hash}",
                title=title,
                description=(
                    "Multiple active files share the same content hash. Review before "
                    "any archive, move, or delete action."
                ),
                pattern={
                    "pattern_type": "duplicate_files",
                    "content_hash": content_hash,
                    "raw_object_ids": [item.raw_object_id for item in items],
                    "titles": [item.title for item in items],
                    "candidate_actions": ["review", "delete_duplicate_files"],
                },
                risk_level="high",
                required_authorization="user_confirmation_required",
                confidence=0.9,
                evidence_ids=evidence_ids,
                project_id=_common_project(items),
            )
        )
    return candidates


def _loose_folder_candidates(
    objects: Sequence[_RawObjectContext],
) -> list[_OpportunityCandidate]:
    folder_groups: dict[str, list[_RawObjectContext]] = {}
    for item in objects:
        folder = _top_folder(item.relative_path)
        if folder.lower() not in {"downloads", "download", "inbox", "archive", "desktop"}:
            continue
        if item.evidence_ids:
            folder_groups.setdefault(folder.lower(), []).append(item)

    candidates: list[_OpportunityCandidate] = []
    for folder, items in folder_groups.items():
        if len(items) < 2:
            continue
        candidates.append(
            _OpportunityCandidate(
                discovery_key=f"loose-folder:{folder}",
                title=f"Prepare a review queue for {folder} files",
                description=(
                    "Several evidence files are sitting in a loose intake folder. "
                    "Create a review checklist before proposing any move."
                ),
                pattern={
                    "pattern_type": "loose_folder",
                    "folder": folder,
                    "raw_object_ids": [item.raw_object_id for item in items],
                    "candidate_actions": ["review", "move_after_authorization"],
                },
                risk_level="high",
                required_authorization="user_confirmation_required",
                confidence=0.7,
                evidence_ids=_evidence_ids(items),
                project_id=_common_project(items),
            )
        )
    return candidates


def _dispersed_project_candidates(
    objects: Sequence[_RawObjectContext],
) -> list[_OpportunityCandidate]:
    by_project: dict[str, list[_RawObjectContext]] = {}
    for item in objects:
        for project_id in item.project_ids:
            if item.evidence_ids:
                by_project.setdefault(project_id, []).append(item)

    candidates: list[_OpportunityCandidate] = []
    for project_id, items in by_project.items():
        folders = sorted({_top_folder(item.relative_path).lower() for item in items})
        if len(items) < 2 or len(folders) < 2:
            continue
        candidates.append(
            _OpportunityCandidate(
                discovery_key=f"project-dispersed:{project_id}:{','.join(folders)}",
                title="Review dispersed project files",
                description=(
                    "Evidence linked to the same project appears across multiple "
                    "folders. Generate an organization plan before any file operation."
                ),
                pattern={
                    "pattern_type": "dispersed_project_files",
                    "project_id": project_id,
                    "folders": folders,
                    "raw_object_ids": [item.raw_object_id for item in items],
                    "candidate_actions": ["review", "move_after_authorization"],
                },
                risk_level="high",
                required_authorization="user_confirmation_required",
                confidence=0.65,
                evidence_ids=_evidence_ids(items),
                project_id=project_id,
            )
        )
    return candidates


def _replace_automation_links(
    connection,
    automation_id: str,
    project_id: str | None,
    evidence_ids: Sequence[str],
    confidence: float,
    now: str,
) -> None:
    connection.execute(
        "DELETE FROM graph_edges WHERE dst_type = 'automation' AND dst_id = ?",
        (automation_id,),
    )
    for evidence_id in evidence_ids:
        connection.execute(
            """
            INSERT INTO graph_edges(
              edge_id,
              src_type,
              src_id,
              dst_type,
              dst_id,
              relation_type,
              confidence,
              evidence_id,
              created_at,
              metadata_json
            )
            VALUES (?, 'evidence', ?, 'automation', ?, 'supports', ?, ?, ?, '{}')
            """,
            (
                generate_id("item"),
                evidence_id,
                automation_id,
                confidence,
                evidence_id,
                now,
            ),
        )

    if project_id:
        connection.execute(
            """
            INSERT OR IGNORE INTO project_links(
              project_id,
              subject_type,
              subject_id,
              relation_type,
              confidence,
              user_confirmed,
              created_at
            )
            VALUES (?, 'automation', ?, 'has_candidate', ?, 0, ?)
            """,
            (project_id, automation_id, confidence, now),
        )


def _evidence_for_automation(connection, automation_id: str) -> list[str]:
    rows = connection.execute(
        """
        SELECT DISTINCT evidence_id
        FROM graph_edges
        WHERE dst_type = 'automation'
          AND dst_id = ?
          AND evidence_id IS NOT NULL
        ORDER BY evidence_id ASC
        """,
        (automation_id,),
    ).fetchall()
    return [row["evidence_id"] for row in rows]


def _row_to_automation(row, evidence_ids: list[str]) -> AutomationOpportunityRecord:
    return AutomationOpportunityRecord(
        automation_id=row["automation_id"],
        project_id=row["project_id"],
        title=row["title"],
        description=row["description"],
        pattern=json.loads(row["pattern_json"]),
        risk_level=row["risk_level"],
        status=row["status"],
        requires_authorization=bool(row["requires_authorization"]),
        source_enhancement_id=row["source_enhancement_id"],
        confidence=row["confidence"],
        metadata=json.loads(row["metadata_json"]),
        evidence_ids=evidence_ids,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _candidate_metadata(
    candidate: _OpportunityCandidate,
    risk_level: str,
    requires_authorization: bool,
) -> dict[str, Any]:
    return {
        "workflow_status": "proposed",
        "discovery_key": candidate.discovery_key,
        "discovery_method": "rule_based_automation_opportunity_v0",
        "suggested_action": candidate.pattern.get("pattern_type"),
        "required_authorization": candidate.required_authorization,
        "risk_reason": _risk_reason(candidate, risk_level),
        "requires_authorization": requires_authorization,
    }


def _effective_risk(candidate: _OpportunityCandidate) -> str:
    actions = candidate.pattern.get("candidate_actions") or []
    if any(_contains_high_risk_action(action) for action in actions):
        return "high"
    return candidate.risk_level


def _requires_authorization(candidate: _OpportunityCandidate, risk_level: str) -> bool:
    return risk_level in {"medium", "high", "critical"} or (
        candidate.required_authorization != "none"
    )


def _risk_reason(candidate: _OpportunityCandidate, risk_level: str) -> str:
    actions = candidate.pattern.get("candidate_actions") or []
    if any(_contains_high_risk_action(action) for action in actions):
        return "Candidate action may move, delete, send, or upload data."
    return f"Rule marked this opportunity as {risk_level} risk."


def _contains_high_risk_action(value: str) -> bool:
    lowered = value.lower()
    return any(action in lowered for action in HIGH_RISK_ACTIONS)


def _evidence_ids(items: Sequence[_RawObjectContext]) -> list[str]:
    evidence_ids: list[str] = []
    for item in items:
        for evidence_id in item.evidence_ids:
            if evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)
    return evidence_ids


def _common_project(items: Sequence[_RawObjectContext]) -> str | None:
    common: set[str] | None = None
    for item in items:
        projects = set(item.project_ids)
        common = projects if common is None else common & projects
    return sorted(common)[0] if common else None


def _top_folder(relative_path: str) -> str:
    parts = [part for part in Path(relative_path).parts if part not in {"", "."}]
    if len(parts) > 1:
        return parts[0]
    return "root"


def _to_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
