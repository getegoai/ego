"""Evidence enhancement pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ego_data_core.kernel.id_generator import generate_id
from ego_data_core.model_router import ModelInputRef, ModelRouter, ModelRunResult
from ego_data_core.nightshift import JobRecord, NightShiftQueue, NightShiftWorker
from ego_data_core.storage.db import get_connection, run_migrations, transaction


ENHANCEMENT_JOB_TYPE = "enhance_evidence"
SUPPORTED_ENHANCEMENT_TYPES = frozenset({"summary", "tag"})
MODEL_PURPOSE_BY_ENHANCEMENT_TYPE = {
    "summary": "summary",
    "tag": "tag",
}
PRIVACY_ORDER = {
    "public": 0,
    "private": 1,
    "sensitive": 2,
    "critical": 3,
}


@dataclass(frozen=True)
class EnhancementRecord:
    enhancement_id: str
    enhancement_type: str
    status: str
    content: dict[str, Any]
    confidence: float | None
    model_id: str | None
    model_runtime: str | None
    prompt_hash: str | None
    privacy_level: str
    metadata: dict[str, Any]
    evidence_ids: list[str]
    generated_at: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class _EvidenceChunk:
    evidence_id: str
    chunk_id: str
    chunk_index: int
    text: str
    privacy_level: str
    title: str | None


class EnhancementService:
    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        queue: NightShiftQueue | None = None,
        model_router: ModelRouter | None = None,
    ) -> None:
        self.database_path = database_path
        self.queue = queue or NightShiftQueue(database_path)
        self.model_router = model_router or ModelRouter(database_path=database_path)

    def create_enhancement_job(
        self,
        *,
        evidence_ids: Sequence[str],
        enhancement_type: str,
        strategy: str = "auto",
        privacy_level: str | None = None,
        priority: int = 2,
    ) -> JobRecord:
        normalized_type = _normalize_enhancement_type(enhancement_type)
        normalized_evidence_ids = _normalize_evidence_ids(evidence_ids)
        normalized_strategy = _normalize_strategy(strategy)
        policy = _policy_from_strategy(normalized_strategy)
        return self.queue.create_job(
            ENHANCEMENT_JOB_TYPE,
            {
                "evidence_ids": normalized_evidence_ids,
                "enhancement_type": normalized_type,
                "strategy": normalized_strategy,
                "privacy_level": privacy_level,
            },
            priority=priority,
            policy=policy,
        )

    def handle_job(self, job: JobRecord) -> dict[str, Any]:
        if job.job_type != ENHANCEMENT_JOB_TYPE:
            raise ValueError(f"Unsupported enhancement job type: {job.job_type}")
        return self.run_enhancement(
            evidence_ids=job.input.get("evidence_ids") or [],
            enhancement_type=str(job.input.get("enhancement_type") or ""),
            job_id=job.job_id,
            policy=job.policy,
            privacy_level=job.input.get("privacy_level"),
        )

    def run_enhancement(
        self,
        *,
        evidence_ids: Sequence[str],
        enhancement_type: str,
        job_id: str | None = None,
        policy: Mapping[str, Any] | None = None,
        privacy_level: str | None = None,
    ) -> dict[str, Any]:
        normalized_type = _normalize_enhancement_type(enhancement_type)
        normalized_evidence_ids = _normalize_evidence_ids(evidence_ids)
        chunks = self._load_chunks(normalized_evidence_ids)
        if not chunks:
            raise ValueError("No evidence text chunks found for enhancement")

        input_refs = [
            ModelInputRef(
                uri=f"chunk://{chunk.chunk_id}",
                text=chunk.text,
                privacy_level=chunk.privacy_level,
                metadata={
                    "evidence_id": chunk.evidence_id,
                    "chunk_index": chunk.chunk_index,
                    "title": chunk.title,
                },
            )
            for chunk in chunks
        ]
        model_result = self.model_router.run(
            MODEL_PURPOSE_BY_ENHANCEMENT_TYPE[normalized_type],
            input_refs,
            policy=policy or {},
            job_id=job_id,
            privacy_level=privacy_level,
        )
        if model_result.status != "succeeded":
            raise RuntimeError(model_result.error_message or "Model router failed")

        invocation = self._get_model_invocation(model_result.invocation_id)
        enhancement_id = self._write_enhancement(
            enhancement_type=normalized_type,
            evidence_ids=normalized_evidence_ids,
            model_result=model_result,
            prompt_hash=invocation["prompt_hash"],
            job_id=job_id,
        )
        return {
            "enhancement_id": enhancement_id,
            "enhancement_type": normalized_type,
            "evidence_ids": normalized_evidence_ids,
            "model_invocation_id": model_result.invocation_id,
            "output_ref_uri": model_result.output_ref_uri,
        }

    def list_enhancements(self, *, evidence_id: str | None = None) -> dict[str, Any]:
        run_migrations(self.database_path)
        params: list[Any] = []
        join_sql = ""
        where_sql = ""
        if evidence_id:
            join_sql = """
            JOIN enhancement_evidence_links filtered_links
              ON filtered_links.enhancement_id = enh.enhancement_id
            """
            where_sql = "WHERE filtered_links.evidence_id = ?"
            params.append(evidence_id)

        with get_connection(self.database_path) as connection:
            rows = connection.execute(
                f"""
                SELECT DISTINCT enh.*
                FROM enhancements enh
                {join_sql}
                {where_sql}
                ORDER BY enh.generated_at DESC, enh.enhancement_id DESC
                """,
                params,
            ).fetchall()
            evidence_rows = connection.execute(
                """
                SELECT enhancement_id, evidence_id
                FROM enhancement_evidence_links
                ORDER BY enhancement_id, evidence_id
                """
            ).fetchall()

        evidence_by_enhancement: dict[str, list[str]] = {}
        for row in evidence_rows:
            evidence_by_enhancement.setdefault(row["enhancement_id"], []).append(
                row["evidence_id"]
            )
        items = [
            enhancement_to_dict(_row_to_enhancement(row, evidence_by_enhancement))
            for row in rows
        ]
        return {"items": items, "total": len(items)}

    def _load_chunks(self, evidence_ids: Sequence[str]) -> list[_EvidenceChunk]:
        run_migrations(self.database_path)
        placeholders = ",".join("?" for _item in evidence_ids)
        with get_connection(self.database_path) as connection:
            evidence_count = connection.execute(
                f"""
                SELECT COUNT(*)
                FROM evidence
                WHERE evidence_id IN ({placeholders})
                """,
                list(evidence_ids),
            ).fetchone()[0]
            if evidence_count != len(evidence_ids):
                missing = sorted(set(evidence_ids) - _existing_evidence_ids(connection, evidence_ids))
                raise ValueError(f"Evidence not found: {', '.join(missing)}")
            rows = connection.execute(
                f"""
                SELECT
                  ev.evidence_id,
                  ev.privacy_level,
                  chunks.chunk_id,
                  chunks.chunk_index,
                  chunks.text,
                  raw.title
                FROM evidence ev
                JOIN evidence_text_chunks chunks ON chunks.evidence_id = ev.evidence_id
                JOIN raw_objects raw ON raw.raw_object_id = ev.raw_object_id
                WHERE ev.evidence_id IN ({placeholders})
                ORDER BY chunks.evidence_id, chunks.chunk_index
                """,
                list(evidence_ids),
            ).fetchall()

        order = {evidence_id: index for index, evidence_id in enumerate(evidence_ids)}
        chunks = [
            _EvidenceChunk(
                evidence_id=row["evidence_id"],
                chunk_id=row["chunk_id"],
                chunk_index=row["chunk_index"],
                text=row["text"],
                privacy_level=row["privacy_level"],
                title=row["title"],
            )
            for row in rows
        ]
        return sorted(chunks, key=lambda item: (order[item.evidence_id], item.chunk_index))

    def _write_enhancement(
        self,
        *,
        enhancement_type: str,
        evidence_ids: Sequence[str],
        model_result: ModelRunResult,
        prompt_hash: str,
        job_id: str | None,
    ) -> str:
        now = _utc_now()
        enhancement_id = generate_id("enh")
        metadata = {
            "model_invocation_id": model_result.invocation_id,
            "output_ref_uri": model_result.output_ref_uri,
            "job_id": job_id,
            "adapter_id": model_result.adapter_id,
        }
        with get_connection(self.database_path) as connection:
            with transaction(connection):
                connection.execute(
                    """
                    INSERT INTO enhancements(
                      enhancement_id,
                      enhancement_type,
                      status,
                      content_json,
                      confidence,
                      model_id,
                      model_runtime,
                      prompt_hash,
                      generated_at,
                      privacy_level,
                      metadata_json,
                      created_at,
                      updated_at
                    )
                    VALUES (?, ?, 'draft', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        enhancement_id,
                        enhancement_type,
                        _to_json(model_result.output),
                        _confidence(model_result.output),
                        model_result.model_id,
                        getattr(self.model_router.adapter, "model_runtime", None),
                        prompt_hash,
                        now,
                        model_result.privacy_level,
                        _to_json(metadata),
                        now,
                        now,
                    ),
                )
                for evidence_id in evidence_ids:
                    connection.execute(
                        """
                        INSERT INTO enhancement_evidence_links(
                          enhancement_id,
                          evidence_id,
                          weight,
                          trace_note,
                          created_at
                        )
                        VALUES (?, ?, 1.0, ?, ?)
                        """,
                        (
                            enhancement_id,
                            evidence_id,
                            f"{enhancement_type} generated from evidence text chunks",
                            now,
                        ),
                    )
        return enhancement_id

    def _get_model_invocation(self, invocation_id: str):
        with get_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM model_invocations WHERE invocation_id = ?",
                (invocation_id,),
            ).fetchone()
        if row is None:
            raise ValueError(f"Model invocation not found: {invocation_id}")
        return row


def register_enhancement_handlers(
    worker: NightShiftWorker,
    service: EnhancementService | None = None,
) -> None:
    worker.register_handler(
        ENHANCEMENT_JOB_TYPE,
        (
            service
            or EnhancementService(
                database_path=worker.queue.database_path,
                queue=worker.queue,
            )
        ).handle_job,
    )


def enhancement_to_dict(record: EnhancementRecord) -> dict[str, Any]:
    return {
        "enhancement_id": record.enhancement_id,
        "enhancement_type": record.enhancement_type,
        "status": record.status,
        "content": record.content,
        "confidence": record.confidence,
        "model_id": record.model_id,
        "model_runtime": record.model_runtime,
        "prompt_hash": record.prompt_hash,
        "privacy_level": record.privacy_level,
        "metadata": record.metadata,
        "evidence_ids": record.evidence_ids,
        "generated_at": record.generated_at,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def _row_to_enhancement(
    row,
    evidence_by_enhancement: Mapping[str, list[str]],
) -> EnhancementRecord:
    return EnhancementRecord(
        enhancement_id=row["enhancement_id"],
        enhancement_type=row["enhancement_type"],
        status=row["status"],
        content=json.loads(row["content_json"]),
        confidence=row["confidence"],
        model_id=row["model_id"],
        model_runtime=row["model_runtime"],
        prompt_hash=row["prompt_hash"],
        privacy_level=row["privacy_level"],
        metadata=json.loads(row["metadata_json"]),
        evidence_ids=evidence_by_enhancement.get(row["enhancement_id"], []),
        generated_at=row["generated_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _normalize_enhancement_type(enhancement_type: str) -> str:
    normalized = enhancement_type.strip().lower()
    if normalized not in SUPPORTED_ENHANCEMENT_TYPES:
        allowed = ", ".join(sorted(SUPPORTED_ENHANCEMENT_TYPES))
        raise ValueError(f"Unsupported enhancement_type '{enhancement_type}'. Allowed: {allowed}")
    return normalized


def _normalize_evidence_ids(evidence_ids: Sequence[str]) -> list[str]:
    normalized = [str(item).strip() for item in evidence_ids if str(item).strip()]
    if not normalized:
        raise ValueError("evidence_ids must not be empty")
    return list(dict.fromkeys(normalized))


def _normalize_strategy(strategy: str) -> str:
    normalized = strategy.strip().lower()
    if normalized not in {"auto", "local_only", "external_allowed"}:
        raise ValueError("strategy must be auto, local_only, or external_allowed")
    return normalized


def _policy_from_strategy(strategy: str) -> dict[str, Any]:
    if strategy == "external_allowed":
        return {"allow_external": True}
    if strategy == "local_only":
        return {"allow_external": False, "preferred_runtime": "rule"}
    return {"allow_external": False}


def _existing_evidence_ids(connection, evidence_ids: Sequence[str]) -> set[str]:
    placeholders = ",".join("?" for _item in evidence_ids)
    rows = connection.execute(
        f"SELECT evidence_id FROM evidence WHERE evidence_id IN ({placeholders})",
        list(evidence_ids),
    ).fetchall()
    return {row["evidence_id"] for row in rows}


def _confidence(output: Mapping[str, Any]) -> float | None:
    value = output.get("confidence")
    return float(value) if isinstance(value, int | float) else None


def _to_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
