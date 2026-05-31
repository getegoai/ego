from pathlib import Path

from ego_data_core.connectors.documents import DocumentParser
from ego_data_core.connectors.filesystem import FilesystemScanner
from ego_data_core.connectors.source_service import SourceService
from ego_data_core.nightshift import NightShiftQueue, NightShiftWorker
from ego_data_core.storage.db import get_connection
from ego_data_core.twin import EnhancementService, register_enhancement_handlers
from ego_data_core.workgraph import ProjectDiscoveryService


def test_project_discovery_groups_evidence_by_directory_and_links_it(
    tmp_path: Path,
) -> None:
    workspace = _make_project_workspace(tmp_path)
    evidence = _scan_parse_and_tag(workspace)

    result = ProjectDiscoveryService().discover_projects()

    assert result["total"] == 2
    names = {item["name"] for item in result["items"]}
    assert names == {"Alpha", "Beta"}
    alpha = next(item for item in result["items"] if item["name"] == "Alpha")
    assert alpha["user_confirmed"] is False
    assert alpha["confidence"] >= 0.65
    assert sorted(alpha["evidence_ids"]) == sorted(
        [evidence["alpha_notes.txt"], evidence["alpha_plan.md"]]
    )

    with get_connection() as connection:
        evidence_links = connection.execute(
            """
            SELECT COUNT(*)
            FROM project_links
            WHERE project_id = ?
              AND subject_type = 'evidence'
            """,
            (alpha["project_id"],),
        ).fetchone()[0]

    assert evidence_links == 2


def test_project_feedback_confirm_reject_and_edit(client, tmp_path: Path) -> None:
    workspace = _make_project_workspace(tmp_path)
    _scan_parse_and_tag(workspace)
    discover = client.post("/api/v1/projects/discover", json={})
    project_id = discover.json()["items"][0]["project_id"]

    confirmed = client.post(
        f"/api/v1/projects/{project_id}/feedback",
        json={"action": "confirm"},
    ).json()
    edited = client.post(
        f"/api/v1/projects/{project_id}/feedback",
        json={
            "action": "edit",
            "name": "Client Alpha",
            "summary": "Edited project summary",
        },
    ).json()
    rejected = client.post(
        f"/api/v1/projects/{project_id}/feedback",
        json={"action": "reject"},
    ).json()

    assert confirmed["user_confirmed"] is True
    assert edited["name"] == "Client Alpha"
    assert edited["summary"] == "Edited project summary"
    assert rejected["status"] == "archived"
    assert rejected["metadata"]["feedback_action"] == "reject"


def test_rejected_project_is_not_regenerated_without_force(tmp_path: Path) -> None:
    workspace = _make_project_workspace(tmp_path)
    _scan_parse_and_tag(workspace)
    service = ProjectDiscoveryService()
    first = service.discover_projects()
    alpha = next(item for item in first["items"] if item["name"] == "Alpha")
    service.apply_feedback(alpha["project_id"], action="reject")

    second = service.discover_projects()
    forced = service.discover_projects(force_regenerate=True)

    assert all(item["name"] != "Alpha" for item in second["items"])
    assert second["skipped_rejected"] == 1
    assert any(item["name"] == "Alpha" for item in forced["items"])


def _make_project_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    alpha = workspace / "alpha"
    beta = workspace / "beta"
    alpha.mkdir(parents=True)
    beta.mkdir()
    (alpha / "alpha_notes.txt").write_text(
        "Alpha project evidence storage notes. Next step: review parser output.",
        encoding="utf-8",
    )
    (alpha / "alpha_plan.md").write_text(
        "# Alpha Plan\n\nBuild evidence-first project workflow.",
        encoding="utf-8",
    )
    (beta / "beta_risk.txt").write_text(
        "Beta project risk: missing source review could delay the work.",
        encoding="utf-8",
    )
    return workspace


def _scan_parse_and_tag(workspace: Path) -> dict[str, str]:
    source = SourceService().create_source(
        source_type="filesystem",
        name="Project Discovery Workspace",
        root_uri=str(workspace),
    )
    FilesystemScanner().scan_source(source.source_id)
    DocumentParser().parse_unparsed_versions()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT raw.title, ev.evidence_id
            FROM evidence ev
            JOIN raw_objects raw ON raw.raw_object_id = ev.raw_object_id
            ORDER BY raw.title
            """
        ).fetchall()
    evidence = {row["title"]: row["evidence_id"] for row in rows}

    queue = NightShiftQueue()
    service = EnhancementService(queue=queue)
    job = service.create_enhancement_job(
        evidence_ids=list(evidence.values()),
        enhancement_type="tag",
    )
    worker = NightShiftWorker(queue, poll_interval_seconds=0)
    register_enhancement_handlers(worker, service)
    worker.run_once()
    assert queue.get_job(job.job_id).status == "succeeded"
    return evidence
