from fastapi.testclient import TestClient

from ego_data_core import __version__


def test_health_returns_ok_and_database_status(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["version"] == __version__
    assert payload["database"]["status"] == "ok"
    assert payload["database"]["foreign_keys"] is True
    assert payload["database"]["migration_count"] == 1
