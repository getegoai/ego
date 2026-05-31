from datetime import datetime, timezone
from pathlib import Path

from ego_data_core.brief import DailyBriefService, DataHealthService
from ego_data_core.connectors.documents import DocumentParser
from ego_data_core.connectors.filesystem import FilesystemScanner
from ego_data_core.connectors.source_service import SourceService
from ego_data_core.model_router import ModelRouter
from ego_data_core.nightshift import NightShiftQueue, NightShiftWorker
from ego_data_core.storage.db import get_connection
from ego_data_core.twin import EnhancementService, register_enhancement_handlers
from ego_data_core.vault import VaultStorage


def test_data_health_reports_empty_day_recommendations() -> None:
    snapshot = DataHealthService().snapshot("2026-01-01")
    brief = DailyBriefService().generate_daily_brief("2026-01-01")

    item = brief.items[0]
    assert snapshot.evidence_count == 0
    assert snapshot.new_file_count == 0
    assert snapshot.recommendations == ["Add a filesystem source and run ego scan <source_id>."]
    assert item["item_type"] == "data_health"
    assert item["metadata"]["metrics"]["evidence_count"] == 0
    assert "Add a filesystem source" in item["body"]

    markdown = VaultStorage().read_text(brief.metadata["markdown_uri"])
    assert "System: data_health" in markdown
    assert "Evidence: none" not in markdown


def test_data_health_reports_parse_enhancement_policy_and_job_status(
    tmp_path: Path,
) -> None:
    target_date = _today_utc()
    evidence = _prepare_health_context(tmp_path)
    _create_policy_block()
    queue = NightShiftQueue()
    queue.mark_failed(
        queue.create_job("demo_failed", max_retries=0).job_id,
        "demo failure",
    )

    service = EnhancementService(queue=queue)
    job = service.create_enhancement_job(
        evidence_ids=[evidence["healthy_note.txt"]],
        enhancement_type="tag",
    )
    worker = NightShiftWorker(queue, poll_interval_seconds=0)
    register_enhancement_handlers(worker, service)
    worker.run_once()
    assert queue.get_job(job.job_id).status == "succeeded"
    queue.create_job("demo_pending")

    brief = DailyBriefService().generate_daily_brief(target_date)
    item = next(item for item in brief.items if item["item_type"] == "data_health")
    metrics = item["metadata"]["metrics"]

    assert metrics["new_file_count"] == 2
    assert metrics["evidence_count"] == 2
    assert metrics["parsed_version_count"] == 1
    assert metrics["parse_failed_count"] == 1
    assert metrics["parse_success_rate"] == 0.5
    assert metrics["enhancement_job_count"] == 1
    assert metrics["enhancement_succeeded_count"] == 1
    assert metrics["enhancement_success_rate"] == 1.0
    assert metrics["enhanced_evidence_count"] == 1
    assert metrics["unenhanced_evidence_count"] == 1
    assert metrics["policy_blocked_count"] == 1
    assert any(job["job_type"] == "document_parse" for job in metrics["failed_jobs"])
    assert any(job["job_type"] == "demo_failed" for job in metrics["failed_jobs"])
    assert any(job["job_type"] == "demo_pending" for job in metrics["pending_jobs"])
    assert item["severity"] == "high"
    assert "Review failed document_parse jobs" in item["body"]
    assert "Privacy policy blocks: 1" in item["body"]


def _prepare_health_context(tmp_path: Path) -> dict[str, str]:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "healthy_note.txt").write_text(
        "Next step: parse and enhance this supported document.",
        encoding="utf-8",
    )
    (workspace / "unsupported.bin").write_bytes(b"\x00\x01demo")
    source = SourceService().create_source(
        source_type="filesystem",
        name="Data Health Workspace",
        root_uri=str(workspace),
    )
    FilesystemScanner().scan_source(source.source_id)
    results = DocumentParser().parse_unparsed_versions()
    assert {item.status for item in results} == {"succeeded", "failed"}

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT raw.title, ev.evidence_id
            FROM evidence ev
            JOIN raw_objects raw ON raw.raw_object_id = ev.raw_object_id
            ORDER BY raw.title
            """
        ).fetchall()
    return {row["title"]: row["evidence_id"] for row in rows}


def _create_policy_block() -> None:
    ModelRouter(adapter=_ExternalAdapter()).run(
        "summary",
        [
            {
                "uri": "chunk://sensitive_health",
                "text": "Sensitive health check text",
                "privacy_level": "sensitive",
            }
        ],
    )


class _ExternalAdapter:
    adapter_id = "external_health_test"
    model_id = None
    model_runtime = "external"
    external_call = True
    supported_purposes = frozenset({"summary"})

    def run(self, purpose, input_refs, policy):
        return {"summary": "external summary"}


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()
