"""Read-only filesystem scanner."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import shutil
from typing import Any
from urllib.parse import unquote, urlparse

from ego_data_core.audit.service import append_audit_log
from ego_data_core.kernel.config import load_settings
from ego_data_core.kernel.id_generator import generate_id
from ego_data_core.storage.db import get_connection, run_migrations, transaction


@dataclass(frozen=True)
class ScanResult:
    source_id: str
    root_path: Path
    scanned_count: int
    created_count: int
    updated_count: int
    skipped_count: int
    evidence_count: int


class FilesystemScanner:
    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = database_path

    def scan_source(self, source_id: str) -> ScanResult:
        run_migrations(self.database_path)
        with get_connection(self.database_path) as connection:
            source = _get_source(connection, source_id)

        if source["source_type"] != "filesystem":
            raise ValueError(f"Source {source_id} is not a filesystem source")
        if not bool(source["enabled"]):
            raise ValueError(f"Source {source_id} is disabled")

        root_path = _path_from_uri(source["root_uri"])
        if not root_path.exists() or not root_path.is_dir():
            raise FileNotFoundError(f"Filesystem source root does not exist: {root_path}")

        scan_policy = json.loads(source["scan_policy_json"])
        files = list(_iter_files(root_path, scan_policy))

        created = 0
        updated = 0
        skipped = 0
        evidence_count = 0

        for file_path in files:
            outcome = self._ingest_file(
                source=source,
                root_path=root_path,
                file_path=file_path,
            )
            if outcome == "created":
                created += 1
                evidence_count += 1
            elif outcome == "updated":
                updated += 1
                evidence_count += 1
            else:
                skipped += 1

        return ScanResult(
            source_id=source_id,
            root_path=root_path,
            scanned_count=len(files),
            created_count=created,
            updated_count=updated,
            skipped_count=skipped,
            evidence_count=evidence_count,
        )

    def _ingest_file(self, *, source, root_path: Path, file_path: Path) -> str:
        stat = file_path.stat()
        content_hash = _sha256(file_path)
        mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        original_uri = file_path.resolve().as_uri()
        modified_at = _datetime_from_timestamp(stat.st_mtime)
        now = _utc_now()
        relative_path = file_path.relative_to(root_path).as_posix()

        with get_connection(self.database_path) as connection:
            existing = connection.execute(
                """
                SELECT *
                FROM raw_objects
                WHERE source_id = ? AND original_uri = ?
                LIMIT 1
                """,
                (source["source_id"], original_uri),
            ).fetchone()

            if existing and existing["content_hash"] == content_hash:
                return "skipped"

            duplicate = connection.execute(
                """
                SELECT raw_object_id, current_version_id
                FROM raw_objects
                WHERE content_hash = ?
                ORDER BY created_at
                LIMIT 1
                """,
                (content_hash,),
            ).fetchone()
            reusable_version = connection.execute(
                """
                SELECT storage_uri
                FROM object_versions
                WHERE content_hash = ?
                ORDER BY captured_at
                LIMIT 1
                """,
                (content_hash,),
            ).fetchone()

            raw_object_id = existing["raw_object_id"] if existing else generate_id("obj")
            version_id = generate_id("ver")
            evidence_id = generate_id("ev")
            version_no = _next_version_no(connection, raw_object_id) if existing else 1
            storage_uri = (
                reusable_version["storage_uri"]
                if reusable_version
                else _copy_to_versions_vault(file_path, version_id)
            )
            metadata = {
                "relative_path": relative_path,
                "scanner": "filesystem_v0",
            }
            if duplicate and duplicate["raw_object_id"] != raw_object_id:
                metadata["duplicate_of_raw_object_id"] = duplicate["raw_object_id"]

            with transaction(connection):
                if existing:
                    connection.execute(
                        """
                        UPDATE raw_objects
                        SET content_hash = ?,
                            size_bytes = ?,
                            mime_type = ?,
                            title = ?,
                            modified_at = ?,
                            captured_at = ?,
                            current_version_id = ?,
                            status = 'active',
                            privacy_level = ?,
                            metadata_json = ?
                        WHERE raw_object_id = ?
                        """,
                        (
                            content_hash,
                            stat.st_size,
                            mime_type,
                            file_path.name,
                            modified_at,
                            now,
                            version_id,
                            source["privacy_level"],
                            _to_json(metadata),
                            raw_object_id,
                        ),
                    )
                else:
                    connection.execute(
                        """
                        INSERT INTO raw_objects(
                          raw_object_id,
                          source_id,
                          object_type,
                          original_uri,
                          canonical_uri,
                          content_hash,
                          size_bytes,
                          mime_type,
                          title,
                          created_at,
                          modified_at,
                          captured_at,
                          current_version_id,
                          status,
                          privacy_level,
                          metadata_json
                        )
                        VALUES (?, ?, 'file', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                        """,
                        (
                            raw_object_id,
                            source["source_id"],
                            original_uri,
                            original_uri,
                            content_hash,
                            stat.st_size,
                            mime_type,
                            file_path.name,
                            now,
                            modified_at,
                            now,
                            version_id,
                            source["privacy_level"],
                            _to_json(metadata),
                        ),
                    )

                connection.execute(
                    """
                    INSERT INTO object_versions(
                      version_id,
                      raw_object_id,
                      version_no,
                      storage_uri,
                      content_hash,
                      size_bytes,
                      captured_at,
                      metadata_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        version_id,
                        raw_object_id,
                        version_no,
                        storage_uri,
                        content_hash,
                        stat.st_size,
                        now,
                        _to_json(metadata),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO evidence(
                      evidence_id,
                      raw_object_id,
                      version_id,
                      evidence_type,
                      evidence_uri,
                      evidence_selector_json,
                      captured_at,
                      content_hash,
                      privacy_level,
                      metadata_json,
                      created_at,
                      updated_at
                    )
                    VALUES (?, ?, ?, 'document', ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        evidence_id,
                        raw_object_id,
                        version_id,
                        storage_uri,
                        _to_json({"type": "whole_file"}),
                        now,
                        content_hash,
                        source["privacy_level"],
                        _to_json(metadata),
                        now,
                        now,
                    ),
                )

        append_audit_log(
            "object_ingested",
            actor="system",
            target={"type": "raw_object", "id": raw_object_id},
            payload={
                "source_id": source["source_id"],
                "version_id": version_id,
                "content_hash": content_hash,
                "size_bytes": stat.st_size,
            },
            database_path=self.database_path,
        )
        append_audit_log(
            "evidence_created",
            actor="system",
            target={"type": "evidence", "id": evidence_id},
            payload={
                "source_id": source["source_id"],
                "raw_object_id": raw_object_id,
                "version_id": version_id,
                "content_hash": content_hash,
            },
            database_path=self.database_path,
        )
        return "updated" if existing else "created"


def _get_source(connection, source_id: str):
    row = connection.execute(
        "SELECT * FROM sources WHERE source_id = ?",
        (source_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Source not found: {source_id}")
    return row


def _iter_files(root_path: Path, scan_policy: dict[str, Any]):
    max_depth = scan_policy.get("max_depth")
    include_globs = scan_policy.get("include_globs") or scan_policy.get("include") or ["*"]
    exclude_globs = scan_policy.get("exclude_globs") or scan_policy.get("exclude") or []

    for candidate in sorted(root_path.rglob("*")):
        if not candidate.is_file():
            continue
        relative = candidate.relative_to(root_path)
        depth = len(relative.parts) - 1
        relative_posix = relative.as_posix()
        if max_depth is not None and depth > int(max_depth):
            continue
        if not _matches_any(relative_posix, candidate.name, include_globs):
            continue
        if _matches_any(relative_posix, candidate.name, exclude_globs):
            continue
        yield candidate


def _matches_any(relative_posix: str, filename: str, patterns: list[str]) -> bool:
    return any(
        fnmatch.fnmatch(relative_posix, pattern) or fnmatch.fnmatch(filename, pattern)
        for pattern in patterns
    )


def _path_from_uri(root_uri: str) -> Path:
    if root_uri.startswith("file://"):
        parsed = urlparse(root_uri)
        raw_path = unquote(parsed.path)
        if os.name == "nt" and raw_path.startswith("/") and ":" in raw_path[:4]:
            raw_path = raw_path[1:]
        return Path(raw_path).expanduser().resolve()
    return Path(root_uri).expanduser().resolve()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_to_versions_vault(file_path: Path, version_id: str) -> str:
    settings = load_settings()
    extension = file_path.suffix.lower()
    stored_name = f"{version_id}{extension}"
    target_path = settings.paths.versions_dir / stored_name
    shutil.copy2(file_path, target_path)
    return f"vault://versions/{stored_name}"


def _next_version_no(connection, raw_object_id: str) -> int:
    row = connection.execute(
        "SELECT COALESCE(MAX(version_no), 0) + 1 FROM object_versions WHERE raw_object_id = ?",
        (raw_object_id,),
    ).fetchone()
    return int(row[0])


def _datetime_from_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
