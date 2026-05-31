import json
from pathlib import Path

from ego_data_core.connectors.filesystem import FilesystemScanner
from ego_data_core.connectors.source_service import SourceService
from ego_data_core.storage.db import get_connection


def test_scan_source_creates_raw_objects_versions_and_evidence(sample_workspace: Path) -> None:
    source = SourceService().create_source(
        source_type="filesystem",
        name="Sample Workspace",
        root_uri=str(sample_workspace),
    )

    result = FilesystemScanner().scan_source(source.source_id)

    assert result.scanned_count == 2
    assert result.created_count == 2
    assert result.updated_count == 0
    assert result.skipped_count == 0
    assert result.evidence_count == 2

    with get_connection() as connection:
        raw_count = connection.execute("SELECT COUNT(*) FROM raw_objects").fetchone()[0]
        version_count = connection.execute("SELECT COUNT(*) FROM object_versions").fetchone()[0]
        evidence_count = connection.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
        raw = connection.execute(
            "SELECT * FROM raw_objects WHERE title = 'notes.txt'"
        ).fetchone()
        version = connection.execute(
            "SELECT * FROM object_versions WHERE raw_object_id = ?",
            (raw["raw_object_id"],),
        ).fetchone()
        evidence = connection.execute(
            "SELECT * FROM evidence WHERE raw_object_id = ?",
            (raw["raw_object_id"],),
        ).fetchone()

    assert raw_count == 2
    assert version_count == 2
    assert evidence_count == 2
    assert raw["content_hash"]
    assert raw["size_bytes"] > 0
    assert raw["mime_type"] == "text/plain"
    assert raw["privacy_level"] == "private"
    assert version["storage_uri"].startswith("vault://versions/")
    assert evidence["evidence_type"] == "document"
    assert evidence["content_hash"] == raw["content_hash"]


def test_scan_is_read_only_for_source_files(sample_workspace: Path) -> None:
    notes = sample_workspace / "notes.txt"
    before_content = notes.read_text(encoding="utf-8")
    before_mtime = notes.stat().st_mtime_ns
    source = SourceService().create_source(
        source_type="filesystem",
        name="Sample Workspace",
        root_uri=str(sample_workspace),
    )

    FilesystemScanner().scan_source(source.source_id)

    assert notes.exists()
    assert notes.read_text(encoding="utf-8") == before_content
    assert notes.stat().st_mtime_ns == before_mtime


def test_scan_respects_include_exclude_and_max_depth(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "keep.txt").write_text("keep", encoding="utf-8")
    (workspace / "skip.txt").write_text("skip", encoding="utf-8")
    nested = workspace / "nested"
    nested.mkdir()
    (nested / "nested.txt").write_text("nested", encoding="utf-8")
    source = SourceService().create_source(
        source_type="filesystem",
        name="Filtered",
        root_uri=str(workspace),
        scan_policy={
            "include_globs": ["*.txt"],
            "exclude_globs": ["skip*"],
            "max_depth": 0,
        },
    )

    result = FilesystemScanner().scan_source(source.source_id)

    assert result.scanned_count == 1
    with get_connection() as connection:
        titles = {
            row["title"]
            for row in connection.execute("SELECT title FROM raw_objects").fetchall()
        }
    assert titles == {"keep.txt"}


def test_scan_marks_duplicate_hash_without_duplicate_vault_copy(
    sample_workspace: Path,
) -> None:
    original = sample_workspace / "notes.txt"
    duplicate = sample_workspace / "notes_copy.txt"
    duplicate.write_bytes(original.read_bytes())
    source = SourceService().create_source(
        source_type="filesystem",
        name="Duplicates",
        root_uri=str(sample_workspace),
    )

    FilesystemScanner().scan_source(source.source_id)

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT ro.raw_object_id, ro.title, ro.metadata_json, ov.storage_uri
            FROM raw_objects ro
            JOIN object_versions ov ON ov.version_id = ro.current_version_id
            WHERE ro.title IN ('notes.txt', 'notes_copy.txt')
            ORDER BY ro.title
            """
        ).fetchall()

    assert len(rows) == 2
    assert rows[0]["storage_uri"] == rows[1]["storage_uri"]
    metadata = [json.loads(row["metadata_json"]) for row in rows]
    assert any("duplicate_of_raw_object_id" in item for item in metadata)


def test_repeated_scan_skips_unchanged_files(sample_workspace: Path) -> None:
    source = SourceService().create_source(
        source_type="filesystem",
        name="Repeated",
        root_uri=str(sample_workspace),
    )
    scanner = FilesystemScanner()
    first = scanner.scan_source(source.source_id)
    second = scanner.scan_source(source.source_id)

    assert first.created_count == 2
    assert second.created_count == 0
    assert second.skipped_count == 2
    with get_connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM object_versions").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 2


def test_modified_file_creates_new_version_and_evidence(sample_workspace: Path) -> None:
    source = SourceService().create_source(
        source_type="filesystem",
        name="Modified",
        root_uri=str(sample_workspace),
        privacy_level="sensitive",
    )
    scanner = FilesystemScanner()
    scanner.scan_source(source.source_id)

    notes = sample_workspace / "notes.txt"
    notes.write_text("changed content", encoding="utf-8")
    result = scanner.scan_source(source.source_id)

    assert result.updated_count == 1
    with get_connection() as connection:
        raw = connection.execute(
            "SELECT * FROM raw_objects WHERE title = 'notes.txt'"
        ).fetchone()
        version_count = connection.execute(
            "SELECT COUNT(*) FROM object_versions WHERE raw_object_id = ?",
            (raw["raw_object_id"],),
        ).fetchone()[0]
        evidence_count = connection.execute(
            "SELECT COUNT(*) FROM evidence WHERE raw_object_id = ?",
            (raw["raw_object_id"],),
        ).fetchone()[0]

    assert raw["privacy_level"] == "sensitive"
    assert version_count == 2
    assert evidence_count == 2


def test_scan_writes_object_and_evidence_audit_events(sample_workspace: Path) -> None:
    source = SourceService().create_source(
        source_type="filesystem",
        name="Audited",
        root_uri=str(sample_workspace),
    )

    FilesystemScanner().scan_source(source.source_id)

    with get_connection() as connection:
        object_events = connection.execute(
            "SELECT COUNT(*) FROM audit_logs WHERE event_type = 'object_ingested'"
        ).fetchone()[0]
        evidence_events = connection.execute(
            "SELECT COUNT(*) FROM audit_logs WHERE event_type = 'evidence_created'"
        ).fetchone()[0]

    assert object_events == 2
    assert evidence_events == 2
