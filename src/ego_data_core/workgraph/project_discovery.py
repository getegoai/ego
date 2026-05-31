"""Rule-based project discovery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Mapping

from ego_data_core.kernel.id_generator import generate_id
from ego_data_core.storage.db import get_connection, run_migrations, transaction


PROJECT_FEEDBACK_ACTIONS = frozenset({"confirm", "reject", "edit"})


@dataclass(frozen=True)
class ProjectRecord:
    project_id: str
    name: str
    status: str
    summary: str | None
    confidence: float | None
    user_confirmed: bool
    metadata: dict[str, Any]
    evidence_ids: list[str]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class _EvidenceSource:
    raw_object_id: str
    evidence_id: str
    title: str
    relative_path: str
    captured_at: str
    enhancements: list[dict[str, Any]]


@dataclass
class _ProjectCandidate:
    discovery_key: str
    name: str
    evidence: list[_EvidenceSource]


class ProjectDiscoveryService:
    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = database_path

    def discover_projects(self, *, force_regenerate: bool = False) -> dict[str, Any]:
        run_migrations(self.database_path)
        sources = self._load_evidence_sources()
        candidates = _build_candidates(sources)
        existing = self._load_projects_by_discovery_key()

        discovered: list[ProjectRecord] = []
        skipped_rejected = 0
        for candidate in candidates:
            existing_record = existing.get(candidate.discovery_key)
            if existing_record and _is_rejected(existing_record) and not force_regenerate:
                skipped_rejected += 1
                continue
            if existing_record and not force_regenerate:
                project_id = existing_record.project_id
                self._link_candidate_evidence(project_id, candidate)
                discovered.append(self.get_project(project_id))
                continue

            project_id = self._create_project_candidate(candidate, force_regenerate)
            discovered.append(self.get_project(project_id))

        return {
            "items": [project_to_dict(project) for project in discovered],
            "total": len(discovered),
            "skipped_rejected": skipped_rejected,
        }

    def list_projects(self) -> dict[str, Any]:
        run_migrations(self.database_path)
        with get_connection(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM projects
                ORDER BY updated_at DESC, project_id DESC
                """
            ).fetchall()
            link_rows = connection.execute(
                """
                SELECT project_id, subject_id
                FROM project_links
                WHERE subject_type = 'evidence'
                ORDER BY project_id, subject_id
                """
            ).fetchall()
        evidence_by_project: dict[str, list[str]] = {}
        for row in link_rows:
            evidence_by_project.setdefault(row["project_id"], []).append(row["subject_id"])
        projects = [_row_to_project(row, evidence_by_project) for row in rows]
        return {
            "items": [project_to_dict(project) for project in projects],
            "total": len(projects),
        }

    def get_project(self, project_id: str) -> ProjectRecord:
        with get_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM projects WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Project not found: {project_id}")
            link_rows = connection.execute(
                """
                SELECT subject_id
                FROM project_links
                WHERE project_id = ?
                  AND subject_type = 'evidence'
                ORDER BY subject_id
                """,
                (project_id,),
            ).fetchall()
        return _row_to_project(
            row,
            {project_id: [link["subject_id"] for link in link_rows]},
        )

    def apply_feedback(
        self,
        project_id: str,
        *,
        action: str,
        name: str | None = None,
        summary: str | None = None,
    ) -> ProjectRecord:
        normalized_action = action.strip().lower()
        if normalized_action not in PROJECT_FEEDBACK_ACTIONS:
            allowed = ", ".join(sorted(PROJECT_FEEDBACK_ACTIONS))
            raise ValueError(f"Unsupported project feedback '{action}'. Allowed: {allowed}")

        project = self.get_project(project_id)
        metadata = dict(project.metadata)
        metadata["feedback_action"] = normalized_action
        metadata["feedback_at"] = _utc_now()

        new_name = name.strip() if name and name.strip() else project.name
        new_summary = summary if summary is not None else project.summary
        new_status = project.status
        user_confirmed = project.user_confirmed
        if normalized_action == "confirm":
            user_confirmed = True
            new_status = "active"
        elif normalized_action == "reject":
            user_confirmed = False
            new_status = "archived"
        elif normalized_action == "edit":
            user_confirmed = True
            new_status = "active"

        now = _utc_now()
        with get_connection(self.database_path) as connection:
            connection.execute(
                """
                UPDATE projects
                SET name = ?,
                    status = ?,
                    summary = ?,
                    user_confirmed = ?,
                    metadata_json = ?,
                    updated_at = ?
                WHERE project_id = ?
                """,
                (
                    new_name,
                    new_status,
                    new_summary,
                    int(user_confirmed),
                    _to_json(metadata),
                    now,
                    project_id,
                ),
            )
            connection.commit()
        return self.get_project(project_id)

    def _load_evidence_sources(self) -> list[_EvidenceSource]:
        with get_connection(self.database_path) as connection:
            evidence_rows = connection.execute(
                """
                SELECT
                  raw.raw_object_id,
                  raw.title,
                  raw.metadata_json AS raw_metadata_json,
                  ev.evidence_id,
                  ev.captured_at
                FROM evidence ev
                JOIN raw_objects raw ON raw.raw_object_id = ev.raw_object_id
                ORDER BY ev.captured_at ASC, ev.evidence_id ASC
                """
            ).fetchall()
            enhancement_rows = connection.execute(
                """
                SELECT
                  link.evidence_id,
                  enh.enhancement_id,
                  enh.enhancement_type,
                  enh.content_json
                FROM enhancement_evidence_links link
                JOIN enhancements enh ON enh.enhancement_id = link.enhancement_id
                ORDER BY enh.generated_at ASC, enh.enhancement_id ASC
                """
            ).fetchall()

        enhancements_by_evidence: dict[str, list[dict[str, Any]]] = {}
        for row in enhancement_rows:
            enhancements_by_evidence.setdefault(row["evidence_id"], []).append(
                {
                    "enhancement_id": row["enhancement_id"],
                    "enhancement_type": row["enhancement_type"],
                    "content": json.loads(row["content_json"]),
                }
            )

        sources: list[_EvidenceSource] = []
        for row in evidence_rows:
            raw_metadata = json.loads(row["raw_metadata_json"])
            sources.append(
                _EvidenceSource(
                    raw_object_id=row["raw_object_id"],
                    evidence_id=row["evidence_id"],
                    title=row["title"] or "Untitled",
                    relative_path=raw_metadata.get("relative_path") or row["title"] or "",
                    captured_at=row["captured_at"],
                    enhancements=enhancements_by_evidence.get(row["evidence_id"], []),
                )
            )
        return sources

    def _load_projects_by_discovery_key(self) -> dict[str, ProjectRecord]:
        projects = self.list_projects()["items"]
        result: dict[str, ProjectRecord] = {}
        for item in projects:
            key = item["metadata"].get("discovery_key")
            if key:
                result[key] = ProjectRecord(
                    project_id=item["project_id"],
                    name=item["name"],
                    status=item["status"],
                    summary=item["summary"],
                    confidence=item["confidence"],
                    user_confirmed=item["user_confirmed"],
                    metadata=item["metadata"],
                    evidence_ids=item["evidence_ids"],
                    created_at=item["created_at"],
                    updated_at=item["updated_at"],
                )
        return result

    def _create_project_candidate(
        self,
        candidate: _ProjectCandidate,
        force_regenerate: bool,
    ) -> str:
        now = _utc_now()
        project_id = generate_id("proj")
        summary = _candidate_summary(candidate)
        metadata = {
            "candidate": True,
            "discovery_key": candidate.discovery_key,
            "discovery_method": "directory_filename_tag_rules",
            "force_regenerated": force_regenerate,
            "evidence_count": len(candidate.evidence),
            "tags": _candidate_tags(candidate),
        }
        with get_connection(self.database_path) as connection:
            with transaction(connection):
                connection.execute(
                    """
                    INSERT INTO projects(
                      project_id,
                      name,
                      status,
                      summary,
                      confidence,
                      user_confirmed,
                      created_at,
                      updated_at,
                      metadata_json
                    )
                    VALUES (?, ?, 'active', ?, ?, 0, ?, ?, ?)
                    """,
                    (
                        project_id,
                        candidate.name,
                        summary,
                        _candidate_confidence(candidate),
                        now,
                        now,
                        _to_json(metadata),
                    ),
                )
                _insert_candidate_links(connection, project_id, candidate, now)
        return project_id

    def _link_candidate_evidence(
        self,
        project_id: str,
        candidate: _ProjectCandidate,
    ) -> None:
        now = _utc_now()
        with get_connection(self.database_path) as connection:
            with transaction(connection):
                _insert_candidate_links(connection, project_id, candidate, now)
                connection.execute(
                    """
                    UPDATE projects
                    SET updated_at = ?
                    WHERE project_id = ?
                    """,
                    (now, project_id),
                )


def project_to_dict(record: ProjectRecord) -> dict[str, Any]:
    return {
        "project_id": record.project_id,
        "name": record.name,
        "status": record.status,
        "summary": record.summary,
        "confidence": record.confidence,
        "user_confirmed": record.user_confirmed,
        "metadata": record.metadata,
        "evidence_ids": record.evidence_ids,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def _row_to_project(
    row,
    evidence_by_project: Mapping[str, list[str]],
) -> ProjectRecord:
    return ProjectRecord(
        project_id=row["project_id"],
        name=row["name"],
        status=row["status"],
        summary=row["summary"],
        confidence=row["confidence"],
        user_confirmed=bool(row["user_confirmed"]),
        metadata=json.loads(row["metadata_json"]),
        evidence_ids=evidence_by_project.get(row["project_id"], []),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _build_candidates(sources: list[_EvidenceSource]) -> list[_ProjectCandidate]:
    grouped: dict[str, list[_EvidenceSource]] = {}
    for source in sources:
        key = _discovery_key(source)
        grouped.setdefault(key, []).append(source)

    candidates = [
        _ProjectCandidate(
            discovery_key=key,
            name=_project_name_from_key(key),
            evidence=items,
        )
        for key, items in grouped.items()
    ]
    return sorted(candidates, key=lambda item: (-len(item.evidence), item.name.lower()))


def _discovery_key(source: _EvidenceSource) -> str:
    path_parts = [part for part in Path(source.relative_path).parts if part not in {"", "."}]
    if len(path_parts) > 1:
        return f"dir:{_slug(path_parts[0])}"
    stem = Path(source.title).stem
    prefix = re.split(r"[_\-\s]+", stem, maxsplit=1)[0]
    if prefix and len(prefix) >= 3:
        return f"file:{_slug(prefix)}"
    tags = _source_tags(source)
    if tags:
        return f"tag:{_slug(tags[0])}"
    return f"file:{_slug(stem or source.evidence_id)}"


def _project_name_from_key(key: str) -> str:
    raw = key.split(":", 1)[1]
    return " ".join(part.capitalize() for part in raw.replace("-", " ").split())


def _candidate_summary(candidate: _ProjectCandidate) -> str:
    titles = ", ".join(item.title for item in candidate.evidence[:3])
    return (
        f"Candidate project inferred from {len(candidate.evidence)} evidence item(s): "
        f"{titles}."
    )


def _candidate_tags(candidate: _ProjectCandidate) -> list[str]:
    tags: list[str] = []
    for source in candidate.evidence:
        for tag in _source_tags(source):
            if tag not in tags:
                tags.append(tag)
    return tags[:10]


def _source_tags(source: _EvidenceSource) -> list[str]:
    tags: list[str] = []
    for enhancement in source.enhancements:
        if enhancement["enhancement_type"] != "tag":
            continue
        for tag in enhancement["content"].get("tags") or []:
            if isinstance(tag, str) and tag not in tags:
                tags.append(tag)
    return tags


def _candidate_confidence(candidate: _ProjectCandidate) -> float:
    base = 0.45
    if len(candidate.evidence) >= 2:
        base += 0.2
    if _candidate_tags(candidate):
        base += 0.1
    return min(base, 0.85)


def _insert_candidate_links(connection, project_id: str, candidate: _ProjectCandidate, now: str) -> None:
    for source in candidate.evidence:
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
            VALUES (?, 'evidence', ?, 'inferred_from', ?, 0, ?)
            """,
            (
                project_id,
                source.evidence_id,
                _candidate_confidence(candidate),
                now,
            ),
        )
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
            VALUES (?, 'raw_object', ?, 'contains', ?, 0, ?)
            """,
            (
                project_id,
                source.raw_object_id,
                _candidate_confidence(candidate),
                now,
            ),
        )


def _is_rejected(project: ProjectRecord) -> bool:
    return project.status == "archived" and project.metadata.get("feedback_action") == "reject"


def _slug(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "-", value.strip().lower())
    return normalized.strip("-") or "untitled"


def _to_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
