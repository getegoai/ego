from fastapi.testclient import TestClient


def test_create_filesystem_source_defaults_to_private_and_writes_audit(
    client: TestClient,
    sample_workspace,
) -> None:
    response = client.post(
        "/api/v1/sources",
        json={
            "source_type": "filesystem",
            "name": "Sample Workspace",
            "root_uri": str(sample_workspace),
        },
    )

    assert response.status_code == 200
    source = response.json()
    assert source["source_id"].startswith("src_")
    assert source["source_type"] == "filesystem"
    assert source["name"] == "Sample Workspace"
    assert source["root_uri"] == str(sample_workspace)
    assert source["enabled"] is True
    assert source["privacy_level"] == "private"
    assert source["scan_policy"] == {}
    assert source["retention_policy"] == {}

    audit_response = client.get(
        "/api/v1/audit/logs",
        params={
            "event_type": "source_created",
            "subject_id": source["source_id"],
        },
    )
    assert audit_response.status_code == 200
    audit_payload = audit_response.json()
    assert audit_payload["total"] == 1
    assert audit_payload["items"][0]["subject_type"] == "source"
    assert audit_payload["items"][0]["detail"]["source_type"] == "filesystem"


def test_list_sources_returns_created_sources(client: TestClient) -> None:
    client.post(
        "/api/v1/sources",
        json={"source_type": "manual", "name": "Manual Notes", "root_uri": "manual://notes"},
    )
    client.post(
        "/api/v1/sources",
        json={"source_type": "browser", "name": "Browser Saves", "root_uri": "browser://saved"},
    )

    response = client.get("/api/v1/sources")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    names = {item["name"] for item in payload["items"]}
    assert names == {"Manual Notes", "Browser Saves"}


def test_create_source_accepts_supported_policies_and_privacy(client: TestClient) -> None:
    response = client.post(
        "/api/v1/sources",
        json={
            "source_type": "screen",
            "name": "Manual Screenshots",
            "root_uri": "screen://manual",
            "privacy_level": "sensitive",
            "scan_policy": {"mode": "manual"},
            "retention_policy": {"retain_days": 30},
        },
    )

    assert response.status_code == 200
    source = response.json()
    assert source["source_type"] == "screen"
    assert source["privacy_level"] == "sensitive"
    assert source["scan_policy"] == {"mode": "manual"}
    assert source["retention_policy"] == {"retain_days": 30}


def test_create_source_accepts_core_source_types(client: TestClient) -> None:
    for source_type in ("filesystem", "screen", "browser", "manual"):
        response = client.post(
            "/api/v1/sources",
            json={
                "source_type": source_type,
                "name": f"{source_type} source",
                "root_uri": f"{source_type}://example",
            },
        )
        assert response.status_code == 200


def test_create_source_rejects_unknown_type(client: TestClient) -> None:
    response = client.post(
        "/api/v1/sources",
        json={
            "source_type": "unknown",
            "name": "Unknown Source",
            "root_uri": "unknown://example",
        },
    )

    assert response.status_code == 422
