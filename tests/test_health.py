from fastapi.testclient import TestClient

from ego_data_core import __version__
from ego_data_core.api.app import app


def test_health_returns_ok_and_database_status() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["version"] == __version__
    assert payload["database"]["status"] == "not_configured"
