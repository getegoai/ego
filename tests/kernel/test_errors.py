from fastapi.testclient import TestClient

from ego_data_core.kernel.errors import ConnectorError, ValidationError
from ego_data_core.kernel.logging import redact_payload
from ego_data_core.nightshift import NightShiftQueue, NightShiftWorker
from ego_data_core.storage.db import get_connection


def test_api_value_error_returns_stable_json(client: TestClient) -> None:
    response = client.post(
        "/api/v1/projects/proj_missing/feedback",
        json={"action": "confirm"},
        headers={"x-request-id": "req_test"},
    )

    payload = response.json()
    assert response.status_code == 400
    assert response.headers["x-request-id"] == "req_test"
    assert payload["code"] == "validation_error"
    assert payload["request_id"] == "req_test"
    assert "Project not found" in payload["message"]


def test_api_request_validation_error_returns_stable_json(client: TestClient) -> None:
    response = client.post(
        "/api/v1/sources",
        json={"source_type": "unknown", "name": "Bad", "root_uri": "bad://source"},
    )

    payload = response.json()
    assert response.status_code == 422
    assert payload["code"] == "request_validation_error"
    assert payload["message"] == "Request validation failed"
    assert payload["request_id"].startswith("req_")
    assert payload["details"]["error_count"] >= 1


def test_redact_payload_hides_sensitive_text_but_keeps_ids() -> None:
    payload = {
        "evidence_id": "ev_123",
        "text": "sensitive project text that should not be logged",
        "nested": {
            "body": "private body text",
            "job_id": "job_123",
        },
    }

    redacted = redact_payload(payload)

    assert redacted["evidence_id"] == "ev_123"
    assert redacted["text"] == "<redacted:48 chars>"
    assert redacted["nested"]["body"] == "<redacted:17 chars>"
    assert redacted["nested"]["job_id"] == "job_123"


def test_worker_records_failed_job_error_and_audit() -> None:
    queue = NightShiftQueue()
    job = queue.create_job(
        "connector_sync",
        {"text": "this raw text should be redacted in logs"},
        max_retries=0,
    )
    worker = NightShiftWorker(queue, poll_interval_seconds=0)

    def fail_handler(_job):
        raise ConnectorError("connector failed")

    worker.register_handler("connector_sync", fail_handler)

    assert worker.run_once() is True
    failed = queue.get_job(job.job_id)
    assert failed.status == "failed"
    assert failed.error_message == "connector failed"

    with get_connection() as connection:
        audit_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM audit_logs
            WHERE event_type = 'job_failed'
              AND subject_id = ?
            """,
            (job.job_id,),
        ).fetchone()[0]

    assert audit_count == 1


def test_ego_error_can_override_code_status_and_details() -> None:
    error = ValidationError(
        "custom validation",
        code="custom_validation",
        status_code=409,
        details={"field": "name"},
    )

    payload = error.to_payload("req_custom").to_dict()

    assert error.status_code == 409
    assert payload == {
        "code": "custom_validation",
        "message": "custom validation",
        "request_id": "req_custom",
        "details": {"field": "name"},
    }
