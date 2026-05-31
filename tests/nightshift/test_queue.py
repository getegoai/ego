import pytest

from ego_data_core.nightshift import NightShiftQueue, NightShiftWorker
from ego_data_core.storage.db import get_connection


def test_create_job_writes_pending_job_and_audit() -> None:
    queue = NightShiftQueue()

    job = queue.create_job(
        "document_parse",
        {"version_id": "ver_test"},
        priority=3,
        policy={"local_only": True},
    )

    assert job.job_id.startswith("job_")
    assert job.status == "pending"
    assert job.job_type == "document_parse"
    assert job.priority == 3
    assert job.input == {"version_id": "ver_test"}
    assert job.policy == {"local_only": True}

    with get_connection() as connection:
        audit = connection.execute(
            """
            SELECT *
            FROM audit_logs
            WHERE event_type = 'job_created'
              AND subject_id = ?
            """,
            (job.job_id,),
        ).fetchone()

    assert audit is not None
    assert audit["subject_type"] == "job"


def test_claim_next_job_uses_priority_then_created_at() -> None:
    queue = NightShiftQueue()
    low_priority = queue.create_job("work", {"name": "low"}, priority=5)
    first_high = queue.create_job("work", {"name": "first"}, priority=1)
    second_high = queue.create_job("work", {"name": "second"}, priority=1)

    claimed = queue.claim_next_job()
    next_claimed = queue.claim_next_job()

    assert claimed.job_id == first_high.job_id
    assert claimed.status == "running"
    assert next_claimed.job_id == second_high.job_id
    assert queue.get_job(low_priority.job_id).status == "pending"


def test_mark_succeeded_records_output_and_audit() -> None:
    queue = NightShiftQueue()
    job = queue.create_job("work")
    claimed = queue.claim_next_job()

    completed = queue.mark_succeeded(claimed.job_id, {"ok": True})

    assert completed.status == "succeeded"
    assert completed.output == {"ok": True}
    assert completed.finished_at is not None
    assert completed.error_message is None

    with get_connection() as connection:
        event_types = {
            row["event_type"]
            for row in connection.execute(
                """
                SELECT event_type
                FROM audit_logs
                WHERE subject_id = ?
                """,
                (job.job_id,),
            ).fetchall()
        }

    assert {"job_created", "job_started", "job_succeeded"}.issubset(event_types)


def test_mark_failed_retries_until_max_retries_then_fails() -> None:
    queue = NightShiftQueue()
    job = queue.create_job("flaky", max_retries=1)
    claimed = queue.claim_next_job()

    retry = queue.mark_failed(claimed.job_id, "first failure")
    claimed_again = queue.claim_next_job()
    terminal = queue.mark_failed(claimed_again.job_id, "second failure")

    assert retry.status == "pending"
    assert retry.retry_count == 1
    assert retry.error_message == "first failure"
    assert claimed_again.job_id == job.job_id
    assert terminal.status == "failed"
    assert terminal.retry_count == 2
    assert terminal.error_message == "second failure"
    assert terminal.finished_at is not None

    with get_connection() as connection:
        failure_events = connection.execute(
            """
            SELECT COUNT(*)
            FROM audit_logs
            WHERE event_type = 'job_failed'
              AND subject_id = ?
            """,
            (job.job_id,),
        ).fetchone()[0]

    assert failure_events == 2


def test_worker_runs_registered_handler() -> None:
    queue = NightShiftQueue()
    job = queue.create_job("echo", {"value": 7})
    worker = NightShiftWorker(queue)
    worker.register_handler("echo", lambda record: {"seen": record.input["value"]})

    processed = worker.run_once()

    assert processed is True
    completed = queue.get_job(job.job_id)
    assert completed.status == "succeeded"
    assert completed.output == {"seen": 7}


def test_worker_blocks_jobs_without_registered_handler() -> None:
    queue = NightShiftQueue()
    job = queue.create_job("missing_handler")
    worker = NightShiftWorker(queue)

    assert worker.run_once() is True

    blocked = queue.get_job(job.job_id)
    assert blocked.status == "blocked"
    assert "No handler registered" in blocked.error_message


def test_worker_can_stop_gracefully_after_current_job() -> None:
    queue = NightShiftQueue()
    job = queue.create_job("stopper")
    worker = NightShiftWorker(queue, poll_interval_seconds=0)

    def stop_handler(_job):
        worker.request_stop()
        return {"stopped": True}

    worker.register_handler("stopper", stop_handler)

    processed_count = worker.run_forever(max_iterations=5)

    assert processed_count == 1
    assert worker.stop_requested is True
    assert queue.get_job(job.job_id).status == "succeeded"


def test_job_payloads_must_be_json_serializable() -> None:
    queue = NightShiftQueue()

    with pytest.raises(ValueError):
        queue.create_job("bad", {"object": object()})
