from pathlib import Path

from ego_data_core.brief import DailyBriefService
from ego_data_core.connectors.documents import DocumentParser
from ego_data_core.connectors.filesystem import FilesystemScanner
from ego_data_core.connectors.source_service import SourceService
from ego_data_core.kernel.time import local_today
from ego_data_core.nightshift import NightShiftQueue, NightShiftWorker
from ego_data_core.storage.db import get_connection
from ego_data_core.twin import EnhancementService, register_enhancement_handlers
from ego_data_core.vault import VaultStorage
from ego_data_core.workgraph import ProjectDiscoveryService, WorkItemExtractor


def test_daily_brief_aggregates_context_exports_markdown_and_audit(
    tmp_path: Path,
) -> None:
    _prepare_daily_brief_context(tmp_path)
    service = DailyBriefService()
    target_date = _today_local()

    brief = service.generate_daily_brief(target_date)

    item_types = {item["item_type"] for item in brief.items}
    assert brief.report_type == "daily"
    assert brief.status == "published"
    assert brief.metadata["markdown_uri"].startswith("vault://briefs/")
    assert "new_evidence" in item_types
    assert "project_update" in item_types
    assert "task" in item_types
    assert "question" in item_types
    assert "risk" in item_types

    for item in brief.items:
        if item["item_type"] in {"new_evidence", "project_update", "task", "question", "risk"}:
            assert item["evidence_ids"]

    markdown = VaultStorage().read_text(brief.metadata["markdown_uri"])
    assert f"# {brief.title}" in markdown
    assert "## Summary" in markdown
    assert "Evidence: [" in markdown

    with get_connection() as connection:
        link_count = connection.execute(
            "SELECT COUNT(*) FROM report_item_evidence_links"
        ).fetchone()[0]
        audit_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM audit_logs
            WHERE event_type = 'brief_generated'
              AND subject_id = ?
            """,
            (brief.report_id,),
        ).fetchone()[0]

    assert link_count >= 5
    assert audit_count == 1


def test_daily_brief_is_idempotent_and_force_regeneration_archives_previous(
    tmp_path: Path,
) -> None:
    _prepare_daily_brief_context(tmp_path)
    service = DailyBriefService()
    target_date = _today_local()

    first = service.generate_daily_brief(target_date)
    second = service.generate_daily_brief(target_date)
    forced = service.generate_daily_brief(target_date, force_regenerate=True)

    assert second.report_id == first.report_id
    assert forced.report_id != first.report_id
    with get_connection() as connection:
        archived_status = connection.execute(
            "SELECT status FROM reports WHERE report_id = ?",
            (first.report_id,),
        ).fetchone()["status"]

    assert archived_status == "archived"


def test_empty_daily_brief_creates_data_health_item_and_api_feedback(client) -> None:
    target_date = "2026-01-01"

    response = client.post(
        "/api/v1/briefs/generate",
        json={"report_type": "daily", "report_date": target_date},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["report_date"] == target_date
    assert payload["items"][0]["item_type"] == "data_health"
    assert payload["metadata"]["markdown_uri"].startswith("vault://briefs/")

    latest = client.get("/api/v1/briefs/daily/latest").json()
    assert latest["report_id"] == payload["report_id"]

    item_id = payload["items"][0]["report_item_id"]
    feedback = client.post(
        f"/api/v1/briefs/items/{item_id}/feedback",
        json={"action": "confirm"},
    ).json()
    assert feedback["user_feedback"] == "confirm"


def _prepare_daily_brief_context(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    project = workspace / "alpha"
    project.mkdir(parents=True)
    (project / "alpha_daily.txt").write_text(
        (
            "Alpha project status. "
            "Next step: create the parser task for daily brief generation. "
            "Question: should we review the source policy before demo? "
            "Risk: missing source review could delay the work."
        ),
        encoding="utf-8",
    )
    source = SourceService().create_source(
        source_type="filesystem",
        name="Daily Brief Workspace",
        root_uri=str(workspace),
    )
    FilesystemScanner().scan_source(source.source_id)
    DocumentParser().parse_unparsed_versions()

    with get_connection() as connection:
        evidence_ids = [
            row["evidence_id"]
            for row in connection.execute("SELECT evidence_id FROM evidence").fetchall()
        ]

    queue = NightShiftQueue()
    service = EnhancementService(queue=queue)
    job = service.create_enhancement_job(
        evidence_ids=evidence_ids,
        enhancement_type="tag",
    )
    worker = NightShiftWorker(queue, poll_interval_seconds=0)
    register_enhancement_handlers(worker, service)
    worker.run_once()
    assert queue.get_job(job.job_id).status == "succeeded"

    ProjectDiscoveryService().discover_projects()
    WorkItemExtractor().extract_items()


def _today_local() -> str:
    return local_today()
