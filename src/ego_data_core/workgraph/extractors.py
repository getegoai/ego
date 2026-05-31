"""Rule-based task, question, and risk extraction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Mapping

from ego_data_core.kernel.id_generator import generate_id
from ego_data_core.model_router import ModelInputRef, ModelRouter
from ego_data_core.storage.db import get_connection, run_migrations, transaction


ITEM_TYPES = frozenset({"task", "question", "risk"})
FEEDBACK_ACTIONS = frozenset({"confirm", "reject", "edit", "later", "convert_to_task"})
QUESTION_CUES = (
    "?",
    "\uff1f",
    "question",
    "unclear",
    "unknown",
    "need clarify",
    "needs clarification",
    "\u95ee\u9898",
    "\u4e0d\u786e\u5b9a",
    "\u662f\u5426",
    "\u5982\u4f55",
    "\u4e3a\u4ec0\u4e48",
    "\u5417",
)


@dataclass(frozen=True)
class WorkItemRecord:
    item_type: str
    item_id: str
    project_id: str | None
    title: str
    body: str | None
    status: str
    priority: str | None
    confidence: float | None
    user_confirmed: bool
    source_enhancement_id: str | None
    metadata: dict[str, Any]
    evidence_ids: list[str]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class _ChunkContext:
    evidence_id: str
    chunk_id: str
    chunk_index: int
    text: str
    privacy_level: str
    project_id: str | None
    source_enhancement_id: str | None


class WorkItemExtractor:
    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        model_router: ModelRouter | None = None,
    ) -> None:
        self.database_path = database_path
        self.model_router = model_router or ModelRouter(database_path=database_path)

    def extract_items(self) -> dict[str, Any]:
        run_migrations(self.database_path)
        chunks = self._load_chunks()
        created = {
            "tasks": [],
            "questions": [],
            "risks": [],
        }

        for chunk in chunks:
            created["tasks"].extend(self._extract_tasks(chunk))
            created["questions"].extend(self._extract_questions(chunk))
            created["risks"].extend(self._extract_risks(chunk))

        return {
            "tasks": [work_item_to_dict(item) for item in created["tasks"]],
            "questions": [work_item_to_dict(item) for item in created["questions"]],
            "risks": [work_item_to_dict(item) for item in created["risks"]],
            "total": sum(len(items) for items in created.values()),
        }

    def list_items(self) -> dict[str, Any]:
        return {
            "tasks": [work_item_to_dict(item) for item in self._list_table_items("task")],
            "questions": [
                work_item_to_dict(item) for item in self._list_table_items("question")
            ],
            "risks": [work_item_to_dict(item) for item in self._list_table_items("risk")],
        }

    def apply_feedback(
        self,
        item_type: str,
        item_id: str,
        *,
        action: str,
        title: str | None = None,
        body: str | None = None,
    ) -> WorkItemRecord:
        normalized_type = _normalize_item_type(item_type)
        normalized_action = _normalize_feedback(action)
        item = self.get_item(normalized_type, item_id)
        metadata = dict(item.metadata)
        metadata["feedback_action"] = normalized_action
        metadata["feedback_at"] = _utc_now()

        if normalized_action == "convert_to_task":
            if normalized_type == "task":
                return item
            return self._convert_to_task(item, title=title, body=body)

        status = item.status
        user_confirmed = item.user_confirmed
        if normalized_action == "confirm":
            user_confirmed = True
        elif normalized_action == "reject":
            status = "cancelled" if normalized_type == "task" else "dismissed"
            user_confirmed = False
        elif normalized_action == "later":
            status = "deferred"
        elif normalized_action == "edit":
            user_confirmed = True

        self._update_item(
            normalized_type,
            item_id,
            status=status,
            title=title if title is not None else item.title,
            body=body if body is not None else item.body,
            user_confirmed=user_confirmed,
            metadata=metadata,
        )
        return self.get_item(normalized_type, item_id)

    def get_item(self, item_type: str, item_id: str) -> WorkItemRecord:
        normalized_type = _normalize_item_type(item_type)
        table, id_column = _table_for_item_type(normalized_type)
        with get_connection(self.database_path) as connection:
            row = connection.execute(
                f"SELECT * FROM {table} WHERE {id_column} = ?",
                (item_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"{normalized_type} not found: {item_id}")
            evidence_ids = _evidence_for_item(connection, normalized_type, item_id)
        return _row_to_work_item(normalized_type, row, evidence_ids)

    def _extract_tasks(self, chunk: _ChunkContext) -> list[WorkItemRecord]:
        result = self.model_router.run(
            "task_candidate",
            [_model_input_ref(chunk)],
        )
        created: list[WorkItemRecord] = []
        for candidate in result.output.get("candidates") or []:
            created.append(
                self._create_task(
                    chunk,
                    title=candidate["title"],
                    description=chunk.text,
                    confidence=candidate.get("confidence", 0.5),
                    model_invocation_id=result.invocation_id,
                )
            )
        return created

    def _extract_risks(self, chunk: _ChunkContext) -> list[WorkItemRecord]:
        result = self.model_router.run(
            "risk_candidate",
            [_model_input_ref(chunk)],
        )
        created: list[WorkItemRecord] = []
        for candidate in result.output.get("candidates") or []:
            created.append(
                self._create_risk(
                    chunk,
                    title=candidate["title"],
                    description=chunk.text,
                    confidence=candidate.get("confidence", 0.5),
                    model_invocation_id=result.invocation_id,
                )
            )
        return created

    def _extract_questions(self, chunk: _ChunkContext) -> list[WorkItemRecord]:
        created: list[WorkItemRecord] = []
        for index, sentence in enumerate(_sentences(chunk.text)):
            lowered = sentence.lower()
            matched = [cue for cue in QUESTION_CUES if cue in lowered]
            if not matched:
                continue
            created.append(
                self._create_question(
                    chunk,
                    title=_shorten(sentence, 180),
                    body=chunk.text,
                    confidence=0.45,
                    metadata={
                        "matched_cues": matched[:3],
                        "sentence_index": index,
                    },
                )
            )
        return created

    def _create_task(
        self,
        chunk: _ChunkContext,
        *,
        title: str,
        description: str,
        confidence: float,
        model_invocation_id: str | None,
    ) -> WorkItemRecord:
        task_id = self._insert_work_item(
            "task",
            chunk,
            title=title,
            body=description,
            confidence=confidence,
            model_invocation_id=model_invocation_id,
            extra_metadata={},
        )
        return self.get_item("task", task_id)

    def _create_question(
        self,
        chunk: _ChunkContext,
        *,
        title: str,
        body: str,
        confidence: float,
        metadata: Mapping[str, Any],
    ) -> WorkItemRecord:
        question_id = self._insert_work_item(
            "question",
            chunk,
            title=title,
            body=body,
            confidence=confidence,
            model_invocation_id=None,
            extra_metadata=metadata,
        )
        return self.get_item("question", question_id)

    def _create_risk(
        self,
        chunk: _ChunkContext,
        *,
        title: str,
        description: str,
        confidence: float,
        model_invocation_id: str | None,
    ) -> WorkItemRecord:
        risk_id = self._insert_work_item(
            "risk",
            chunk,
            title=title,
            body=description,
            confidence=confidence,
            model_invocation_id=model_invocation_id,
            extra_metadata={},
        )
        return self.get_item("risk", risk_id)

    def _insert_work_item(
        self,
        item_type: str,
        chunk: _ChunkContext,
        *,
        title: str,
        body: str,
        confidence: float,
        model_invocation_id: str | None,
        extra_metadata: Mapping[str, Any],
    ) -> str:
        existing_id = self._find_existing_item(item_type, chunk.evidence_id, title)
        if existing_id:
            return existing_id

        now = _utc_now()
        item_id = generate_id(_id_prefix_for_item_type(item_type))
        metadata = {
            "workflow_status": "proposed",
            "evidence_ids": [chunk.evidence_id],
            "chunk_id": chunk.chunk_id,
            "chunk_index": chunk.chunk_index,
            "model_invocation_id": model_invocation_id,
            **dict(extra_metadata),
        }
        with get_connection(self.database_path) as connection:
            with transaction(connection):
                if item_type == "task":
                    connection.execute(
                        """
                        INSERT INTO tasks(
                          task_id,
                          project_id,
                          title,
                          description,
                          status,
                          priority,
                          source_enhancement_id,
                          confidence,
                          user_confirmed,
                          created_at,
                          updated_at,
                          metadata_json
                        )
                        VALUES (?, ?, ?, ?, 'open', 'medium', ?, ?, 0, ?, ?, ?)
                        """,
                        (
                            item_id,
                            chunk.project_id,
                            title,
                            body,
                            chunk.source_enhancement_id,
                            confidence,
                            now,
                            now,
                            _to_json(metadata),
                        ),
                    )
                elif item_type == "question":
                    connection.execute(
                        """
                        INSERT INTO questions(
                          question_id,
                          project_id,
                          title,
                          body,
                          status,
                          importance,
                          source_enhancement_id,
                          confidence,
                          user_confirmed,
                          created_at,
                          updated_at,
                          metadata_json
                        )
                        VALUES (?, ?, ?, ?, 'open', 'medium', ?, ?, 0, ?, ?, ?)
                        """,
                        (
                            item_id,
                            chunk.project_id,
                            title,
                            body,
                            chunk.source_enhancement_id,
                            confidence,
                            now,
                            now,
                            _to_json(metadata),
                        ),
                    )
                elif item_type == "risk":
                    connection.execute(
                        """
                        INSERT INTO risks(
                          risk_id,
                          project_id,
                          title,
                          description,
                          risk_level,
                          status,
                          source_enhancement_id,
                          confidence,
                          user_confirmed,
                          created_at,
                          updated_at,
                          metadata_json
                        )
                        VALUES (?, ?, ?, ?, 'medium', 'open', ?, ?, 0, ?, ?, ?)
                        """,
                        (
                            item_id,
                            chunk.project_id,
                            title,
                            body,
                            chunk.source_enhancement_id,
                            confidence,
                            now,
                            now,
                            _to_json(metadata),
                        ),
                    )
                _link_item_to_evidence(
                    connection,
                    item_type,
                    item_id,
                    chunk.evidence_id,
                    confidence,
                    now,
                )
                if chunk.project_id:
                    _link_item_to_project(
                        connection,
                        item_type,
                        item_id,
                        chunk.project_id,
                        confidence,
                        now,
                    )
        return item_id

    def _find_existing_item(self, item_type: str, evidence_id: str, title: str) -> str | None:
        table, id_column = _table_for_item_type(item_type)
        with get_connection(self.database_path) as connection:
            rows = connection.execute(
                f"SELECT {id_column}, metadata_json FROM {table} WHERE title = ?",
                (title,),
            ).fetchall()
        for row in rows:
            metadata = json.loads(row["metadata_json"])
            if evidence_id in metadata.get("evidence_ids", []):
                return row[id_column]
        return None

    def _load_chunks(self) -> list[_ChunkContext]:
        with get_connection(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT
                  chunks.chunk_id,
                  chunks.evidence_id,
                  chunks.chunk_index,
                  chunks.text,
                  ev.privacy_level
                FROM evidence_text_chunks chunks
                JOIN evidence ev ON ev.evidence_id = chunks.evidence_id
                ORDER BY chunks.evidence_id, chunks.chunk_index
                """
            ).fetchall()
            project_rows = connection.execute(
                """
                SELECT project_id, subject_id AS evidence_id
                FROM project_links
                WHERE subject_type = 'evidence'
                ORDER BY created_at ASC
                """
            ).fetchall()
            enhancement_rows = connection.execute(
                """
                SELECT enhancement_id, evidence_id
                FROM enhancement_evidence_links
                ORDER BY created_at ASC
                """
            ).fetchall()

        project_by_evidence: dict[str, str] = {}
        for row in project_rows:
            project_by_evidence.setdefault(row["evidence_id"], row["project_id"])
        enhancement_by_evidence: dict[str, str] = {}
        for row in enhancement_rows:
            enhancement_by_evidence.setdefault(row["evidence_id"], row["enhancement_id"])

        return [
            _ChunkContext(
                evidence_id=row["evidence_id"],
                chunk_id=row["chunk_id"],
                chunk_index=row["chunk_index"],
                text=row["text"],
                privacy_level=row["privacy_level"],
                project_id=project_by_evidence.get(row["evidence_id"]),
                source_enhancement_id=enhancement_by_evidence.get(row["evidence_id"]),
            )
            for row in rows
        ]

    def _list_table_items(self, item_type: str) -> list[WorkItemRecord]:
        table, id_column = _table_for_item_type(item_type)
        with get_connection(self.database_path) as connection:
            rows = connection.execute(
                f"SELECT * FROM {table} ORDER BY created_at ASC, {id_column} ASC"
            ).fetchall()
            evidence_by_item = {
                row[id_column]: _evidence_for_item(connection, item_type, row[id_column])
                for row in rows
            }
        return [
            _row_to_work_item(item_type, row, evidence_by_item[row[id_column]])
            for row in rows
        ]

    def _update_item(
        self,
        item_type: str,
        item_id: str,
        *,
        status: str,
        title: str,
        body: str | None,
        user_confirmed: bool,
        metadata: Mapping[str, Any],
    ) -> None:
        table, id_column = _table_for_item_type(item_type)
        body_column = "description" if item_type in {"task", "risk"} else "body"
        now = _utc_now()
        with get_connection(self.database_path) as connection:
            connection.execute(
                f"""
                UPDATE {table}
                SET title = ?,
                    {body_column} = ?,
                    status = ?,
                    user_confirmed = ?,
                    metadata_json = ?,
                    updated_at = ?
                WHERE {id_column} = ?
                """,
                (
                    title,
                    body,
                    status,
                    int(user_confirmed),
                    _to_json(metadata),
                    now,
                    item_id,
                ),
            )
            connection.commit()

    def _convert_to_task(
        self,
        item: WorkItemRecord,
        *,
        title: str | None,
        body: str | None,
    ) -> WorkItemRecord:
        evidence_id = item.evidence_ids[0]
        chunk = _ChunkContext(
            evidence_id=evidence_id,
            chunk_id=item.metadata.get("chunk_id") or "",
            chunk_index=int(item.metadata.get("chunk_index") or 0),
            text=body or item.body or item.title,
            privacy_level="private",
            project_id=item.project_id,
            source_enhancement_id=item.source_enhancement_id,
        )
        task = self._create_task(
            chunk,
            title=title or item.title,
            description=body or item.body or item.title,
            confidence=item.confidence or 0.4,
            model_invocation_id=item.metadata.get("model_invocation_id"),
        )
        metadata = dict(item.metadata)
        metadata["converted_to_task_id"] = task.item_id
        metadata["feedback_action"] = "convert_to_task"
        self._update_item(
            item.item_type,
            item.item_id,
            status="deferred",
            title=item.title,
            body=item.body,
            user_confirmed=item.user_confirmed,
            metadata=metadata,
        )
        return task


def work_item_to_dict(record: WorkItemRecord) -> dict[str, Any]:
    return {
        "item_type": record.item_type,
        "item_id": record.item_id,
        "project_id": record.project_id,
        "title": record.title,
        "body": record.body,
        "status": record.status,
        "priority": record.priority,
        "confidence": record.confidence,
        "user_confirmed": record.user_confirmed,
        "source_enhancement_id": record.source_enhancement_id,
        "metadata": record.metadata,
        "evidence_ids": record.evidence_ids,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def _row_to_work_item(item_type: str, row, evidence_ids: list[str]) -> WorkItemRecord:
    id_column = _table_for_item_type(item_type)[1]
    body = row["description"] if item_type in {"task", "risk"} else row["body"]
    priority = row["priority"] if item_type == "task" else row["importance"] if item_type == "question" else row["risk_level"]
    return WorkItemRecord(
        item_type=item_type,
        item_id=row[id_column],
        project_id=row["project_id"],
        title=row["title"],
        body=body,
        status=row["status"],
        priority=priority,
        confidence=row["confidence"],
        user_confirmed=bool(row["user_confirmed"]),
        source_enhancement_id=row["source_enhancement_id"],
        metadata=json.loads(row["metadata_json"]),
        evidence_ids=evidence_ids,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _model_input_ref(chunk: _ChunkContext) -> ModelInputRef:
    return ModelInputRef(
        uri=f"chunk://{chunk.chunk_id}",
        text=chunk.text,
        privacy_level=chunk.privacy_level,
        metadata={
            "evidence_id": chunk.evidence_id,
            "chunk_index": chunk.chunk_index,
        },
    )


def _normalize_item_type(item_type: str) -> str:
    normalized = item_type.strip().lower()
    if normalized not in ITEM_TYPES:
        allowed = ", ".join(sorted(ITEM_TYPES))
        raise ValueError(f"Unsupported item_type '{item_type}'. Allowed: {allowed}")
    return normalized


def _normalize_feedback(action: str) -> str:
    normalized = action.strip().lower()
    if normalized not in FEEDBACK_ACTIONS:
        allowed = ", ".join(sorted(FEEDBACK_ACTIONS))
        raise ValueError(f"Unsupported feedback action '{action}'. Allowed: {allowed}")
    return normalized


def _table_for_item_type(item_type: str) -> tuple[str, str]:
    if item_type == "task":
        return "tasks", "task_id"
    if item_type == "question":
        return "questions", "question_id"
    if item_type == "risk":
        return "risks", "risk_id"
    raise ValueError(f"Unsupported item_type: {item_type}")


def _id_prefix_for_item_type(item_type: str) -> str:
    if item_type == "task":
        return "task"
    if item_type == "question":
        return "q"
    if item_type == "risk":
        return "risk"
    raise ValueError(f"Unsupported item_type: {item_type}")


def _link_item_to_evidence(
    connection,
    item_type: str,
    item_id: str,
    evidence_id: str,
    confidence: float,
    now: str,
) -> None:
    edge_id = generate_id("item")
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
        VALUES (?, 'evidence', ?, ?, ?, 'supports', ?, ?, ?, '{}')
        """,
        (edge_id, evidence_id, item_type, item_id, confidence, evidence_id, now),
    )


def _link_item_to_project(
    connection,
    item_type: str,
    item_id: str,
    project_id: str,
    confidence: float,
    now: str,
) -> None:
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
        VALUES (?, ?, ?, 'has_candidate', ?, 0, ?)
        """,
        (project_id, item_type, item_id, confidence, now),
    )


def _evidence_for_item(connection, item_type: str, item_id: str) -> list[str]:
    rows = connection.execute(
        """
        SELECT DISTINCT evidence_id
        FROM graph_edges
        WHERE dst_type = ?
          AND dst_id = ?
          AND evidence_id IS NOT NULL
        ORDER BY evidence_id
        """,
        (item_type, item_id),
    ).fetchall()
    return [row["evidence_id"] for row in rows]


def _sentences(text: str) -> list[str]:
    cleaned = " ".join(text.split())
    parts = re.split(r"(?<=[.!?\u3002\uff01\uff1f])\s+", cleaned)
    return [part.strip() for part in parts if part.strip()]


def _shorten(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3].rstrip()}..."


def _to_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
