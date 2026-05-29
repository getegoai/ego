import pytest

from ego_data_core.audit.service import (
    AuditService,
    KNOWN_AUDIT_EVENT_TYPES,
    append_audit_log,
    list_audit_logs,
)


def test_append_audit_log_writes_record_and_json_detail() -> None:
    record = append_audit_log(
        "source_created",
        actor={"type": "user", "id": "usr_test"},
        target={"type": "source", "id": "src_test"},
        payload={"name": "Sample Source", "privacy_level": "private"},
    )

    assert record.audit_id.startswith("aud_")
    assert record.event_type == "source_created"
    assert record.actor_type == "user"
    assert record.actor_id == "usr_test"
    assert record.subject_type == "source"
    assert record.subject_id == "src_test"
    assert record.detail["privacy_level"] == "private"
    assert record.prev_hash is None
    assert len(record.event_hash) == 64

    result = list_audit_logs()
    assert result["total"] == 1
    assert result["items"][0]["detail"]["name"] == "Sample Source"


def test_append_audit_log_chains_hashes() -> None:
    first = append_audit_log(
        "job_created",
        actor="system",
        target={"type": "job", "id": "job_test_1"},
        payload={"job_type": "scan"},
    )
    second = append_audit_log(
        "error",
        actor="system",
        target={"type": "job", "id": "job_test_1"},
        payload={"code": "scan_failed", "message": "sample failure"},
    )

    assert second.prev_hash == first.event_hash
    assert second.event_hash != first.event_hash


def test_list_audit_logs_supports_pagination_and_filters() -> None:
    append_audit_log("source_created", target={"type": "source", "id": "src_1"})
    append_audit_log("source_created", target={"type": "source", "id": "src_2"})
    append_audit_log("policy_blocked", target={"type": "source", "id": "src_2"})

    page = list_audit_logs(limit=1, offset=1)
    assert page["limit"] == 1
    assert page["offset"] == 1
    assert page["total"] == 3
    assert len(page["items"]) == 1

    filtered = list_audit_logs(event_type="source_created", subject_id="src_2")
    assert filtered["total"] == 1
    assert filtered["items"][0]["event_type"] == "source_created"
    assert filtered["items"][0]["subject_id"] == "src_2"


def test_error_event_is_supported() -> None:
    assert "error" in KNOWN_AUDIT_EVENT_TYPES

    record = append_audit_log(
        "error",
        payload={"code": "boom", "message": "A controlled test error"},
    )

    assert record.event_type == "error"
    assert record.detail["code"] == "boom"


def test_service_exposes_no_update_or_delete_methods() -> None:
    service = AuditService()

    assert not hasattr(service, "update_audit_log")
    assert not hasattr(service, "delete_audit_log")


def test_invalid_actor_type_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="Invalid actor_type"):
        append_audit_log("source_created", actor="robot")


def test_non_json_payload_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="JSON serializable"):
        append_audit_log("source_created", payload={"bad": object()})


def test_audit_logs_api_returns_paginated_logs(client) -> None:
    append_audit_log(
        "source_created",
        actor={"type": "user", "id": "usr_api"},
        target={"type": "source", "id": "src_api"},
        payload={"name": "API Source"},
    )

    response = client.get("/api/v1/audit/logs", params={"limit": 10, "offset": 0})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["event_type"] == "source_created"
    assert payload["items"][0]["detail"]["name"] == "API Source"
