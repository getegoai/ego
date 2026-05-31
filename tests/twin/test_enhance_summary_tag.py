import json
from pathlib import Path

from ego_data_core.connectors.documents import DocumentParser
from ego_data_core.connectors.filesystem import FilesystemScanner
from ego_data_core.connectors.source_service import SourceService
from ego_data_core.nightshift import NightShiftQueue, NightShiftWorker
from ego_data_core.storage.db import get_connection
from ego_data_core.twin import EnhancementService, register_enhancement_handlers


def test_post_twin_enhance_creates_job(client, sample_workspace: Path) -> None:
    evidence = _prepare_parsed_evidence(sample_workspace)

    response = client.post(
        "/api/v1/twin/enhance",
        json={
            "evidence_ids": [evidence["notes.txt"]],
            "enhancement_type": "summary",
            "strategy": "local_only",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"].startswith("job_")
    assert payload["job_type"] == "enhance_evidence"
    assert payload["status"] == "pending"
    assert payload["input"]["enhancement_type"] == "summary"

    with get_connection() as connection:
        job = connection.execute(
            "SELECT * FROM jobs WHERE job_id = ?",
            (payload["job_id"],),
        ).fetchone()
        audit_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM audit_logs
            WHERE event_type = 'job_created'
              AND subject_id = ?
            """,
            (payload["job_id"],),
        ).fetchone()[0]

    assert json.loads(job["input_json"])["evidence_ids"] == [evidence["notes.txt"]]
    assert audit_count == 1


def test_worker_executes_summary_enhancement_and_links_evidence(
    sample_workspace: Path,
) -> None:
    evidence = _prepare_parsed_evidence(sample_workspace)
    queue = NightShiftQueue()
    service = EnhancementService(queue=queue)
    job = service.create_enhancement_job(
        evidence_ids=[evidence["notes.txt"]],
        enhancement_type="summary",
    )
    worker = NightShiftWorker(queue, poll_interval_seconds=0)
    register_enhancement_handlers(worker, service)

    assert worker.run_once() is True

    completed = queue.get_job(job.job_id)
    assert completed.status == "succeeded"
    enhancement_id = completed.output["enhancement_id"]

    with get_connection() as connection:
        enhancement = connection.execute(
            "SELECT * FROM enhancements WHERE enhancement_id = ?",
            (enhancement_id,),
        ).fetchone()
        link = connection.execute(
            """
            SELECT *
            FROM enhancement_evidence_links
            WHERE enhancement_id = ?
            """,
            (enhancement_id,),
        ).fetchone()
        invocation_id = json.loads(enhancement["metadata_json"])["model_invocation_id"]
        invocation = connection.execute(
            "SELECT * FROM model_invocations WHERE invocation_id = ?",
            (invocation_id,),
        ).fetchone()

    content = json.loads(enhancement["content_json"])
    assert enhancement["enhancement_type"] == "summary"
    assert enhancement["status"] == "draft"
    assert "Ego Data Core sample note" in content["summary"]
    assert enhancement["model_runtime"] == "rule"
    assert enhancement["prompt_hash"] == invocation["prompt_hash"]
    assert link["evidence_id"] == evidence["notes.txt"]
    assert invocation["job_id"] == job.job_id


def test_tag_enhancement_can_be_queried_by_evidence_id(
    client,
    sample_workspace: Path,
) -> None:
    evidence = _prepare_parsed_evidence(sample_workspace)
    evidence_ids = [evidence["notes.txt"], evidence["project_plan.md"]]
    queue = NightShiftQueue()
    service = EnhancementService(queue=queue)
    job = service.create_enhancement_job(
        evidence_ids=evidence_ids,
        enhancement_type="tag",
    )
    worker = NightShiftWorker(queue, poll_interval_seconds=0)
    register_enhancement_handlers(worker, service)

    worker.run_once()

    completed = queue.get_job(job.job_id)
    assert completed.status == "succeeded"

    response = client.get(
        "/api/v1/twin/enhancements",
        params={"evidence_id": evidence["project_plan.md"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    item = payload["items"][0]
    assert item["enhancement_type"] == "tag"
    assert "evidence" in item["content"]["tags"]
    assert sorted(item["evidence_ids"]) == sorted(evidence_ids)


def test_enhancement_requires_existing_evidence(sample_workspace: Path) -> None:
    _prepare_parsed_evidence(sample_workspace)
    service = EnhancementService()

    try:
        service.run_enhancement(
            evidence_ids=["ev_missing"],
            enhancement_type="summary",
        )
    except ValueError as exc:
        assert "Evidence not found" in str(exc)
    else:
        raise AssertionError("missing evidence should fail")


def _prepare_parsed_evidence(sample_workspace: Path) -> dict[str, str]:
    source = SourceService().create_source(
        source_type="filesystem",
        name="Enhancement Workspace",
        root_uri=str(sample_workspace),
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
    return {row["title"]: row["evidence_id"] for row in rows}
