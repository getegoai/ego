from pathlib import Path

from ego_data_core.connectors.documents import DocumentParser
from ego_data_core.connectors.filesystem import FilesystemScanner
from ego_data_core.connectors.source_service import SourceService
from ego_data_core.nightshift import NightShiftQueue, NightShiftWorker
from ego_data_core.storage.db import get_connection
from ego_data_core.twin import EnhancementService, register_enhancement_handlers
from ego_data_core.workgraph import ProjectDiscoveryService, WorkItemExtractor


def test_extract_items_creates_tasks_questions_and_risks_with_evidence_links(
    tmp_path: Path,
) -> None:
    _prepare_workgraph_context(tmp_path)

    result = WorkItemExtractor().extract_items()

    assert result["total"] >= 3
    assert result["tasks"]
    assert result["questions"]
    assert result["risks"]

    for collection in ("tasks", "questions", "risks"):
        item = result[collection][0]
        assert item["project_id"] is not None
        assert item["evidence_ids"]
        assert item["source_enhancement_id"] is not None
        assert item["metadata"]["workflow_status"] == "proposed"
        assert item["confidence"] > 0

    with get_connection() as connection:
        edge_count = connection.execute(
            "SELECT COUNT(*) FROM graph_edges WHERE relation_type = 'supports'"
        ).fetchone()[0]
        project_item_links = connection.execute(
            """
            SELECT COUNT(*)
            FROM project_links
            WHERE subject_type IN ('task', 'question', 'risk')
            """
        ).fetchone()[0]

    assert edge_count >= 3
    assert project_item_links >= 3


def test_extraction_is_idempotent_for_same_evidence_and_title(tmp_path: Path) -> None:
    _prepare_workgraph_context(tmp_path)
    extractor = WorkItemExtractor()

    first = extractor.extract_items()
    second = extractor.extract_items()

    assert first["total"] >= 3
    assert second["total"] == first["total"]
    with get_connection() as connection:
        task_count = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        question_count = connection.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        risk_count = connection.execute("SELECT COUNT(*) FROM risks").fetchone()[0]

    assert task_count == len(first["tasks"])
    assert question_count == len(first["questions"])
    assert risk_count == len(first["risks"])


def test_work_item_feedback_and_convert_to_task(client, tmp_path: Path) -> None:
    _prepare_workgraph_context(tmp_path)
    extract_response = client.post("/api/v1/workgraph/extract")

    payload = extract_response.json()
    task_id = payload["tasks"][0]["item_id"]
    question_id = payload["questions"][0]["item_id"]
    risk_id = payload["risks"][0]["item_id"]

    confirmed = client.post(
        f"/api/v1/workgraph/items/task/{task_id}/feedback",
        json={"action": "confirm"},
    ).json()
    converted = client.post(
        f"/api/v1/workgraph/items/question/{question_id}/feedback",
        json={"action": "convert_to_task", "title": "Clarify open question"},
    ).json()
    rejected = client.post(
        f"/api/v1/workgraph/items/risk/{risk_id}/feedback",
        json={"action": "reject"},
    ).json()

    assert confirmed["user_confirmed"] is True
    assert converted["item_type"] == "task"
    assert converted["title"] == "Clarify open question"
    assert rejected["status"] == "dismissed"


def _prepare_workgraph_context(tmp_path: Path) -> dict[str, str]:
    workspace = tmp_path / "workspace"
    project = workspace / "alpha"
    project.mkdir(parents=True)
    (project / "alpha_brief.txt").write_text(
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
        name="Extractor Workspace",
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

    ProjectDiscoveryService().discover_projects()
    return evidence
