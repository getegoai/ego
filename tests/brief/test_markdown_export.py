from pathlib import Path

from ego_data_core.brief import BriefMarkdownExporter, DailyBriefService
from ego_data_core.connectors.documents import DocumentParser
from ego_data_core.connectors.filesystem import FilesystemScanner
from ego_data_core.connectors.source_service import SourceService
from ego_data_core.kernel.time import local_today
from ego_data_core.nightshift import NightShiftQueue, NightShiftWorker
from ego_data_core.storage.db import get_connection
from ego_data_core.twin import EnhancementService, register_enhancement_handlers
from ego_data_core.vault import VaultStorage
from ego_data_core.workgraph import ProjectDiscoveryService, WorkItemExtractor


def test_markdown_export_uses_stable_evidence_references_without_absolute_paths(
    tmp_path: Path,
) -> None:
    _prepare_export_context(tmp_path)
    brief = DailyBriefService().generate_daily_brief(_today_local())

    markdown = BriefMarkdownExporter().render_report(brief)

    evidence_id = brief.items[0]["evidence_ids"][0]
    assert f"Evidence: [{evidence_id}]" in markdown
    assert "alpha/alpha_export.txt" in markdown
    assert "Alpha export status" in markdown
    assert "file:///" not in markdown
    assert str(tmp_path) not in markdown


def test_markdown_export_writes_to_briefs_vault(tmp_path: Path) -> None:
    _prepare_export_context(tmp_path)
    brief = DailyBriefService().generate_daily_brief(_today_local())
    exporter = BriefMarkdownExporter()

    uri = exporter.export_report(brief)

    assert uri.startswith("vault://briefs/")
    markdown = VaultStorage().read_text(uri)
    assert markdown.startswith(f"# {brief.title}")
    assert "## Sections" in markdown
    assert "Evidence: [ev_" in markdown


def _prepare_export_context(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    project = workspace / "alpha"
    project.mkdir(parents=True)
    (project / "alpha_export.txt").write_text(
        (
            "Alpha export status. "
            "Next step: create the Markdown export task. "
            "Question: should evidence references hide absolute paths? "
            "Risk: leaking a local path could expose private context."
        ),
        encoding="utf-8",
    )
    source = SourceService().create_source(
        source_type="filesystem",
        name="Markdown Export Workspace",
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
