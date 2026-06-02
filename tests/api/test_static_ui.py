from fastapi.testclient import TestClient


def test_static_ui_root_serves_local_app(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Ego Data Core" in response.text
    assert 'data-api-base="/api/v1"' in response.text
    assert 'src="/ui/app.js"' in response.text
    assert 'href="/ui/favicon.svg"' in response.text


def test_static_ui_assets_are_served_and_local_only(client: TestClient) -> None:
    script = client.get("/ui/app.js")
    styles = client.get("/ui/styles.css")
    favicon = client.get("/ui/favicon.svg")

    assert script.status_code == 200
    assert styles.status_code == 200
    assert favicon.status_code == 200
    assert "/api/v1" in script.text
    assert "/search?" in script.text
    assert "https://" not in script.text
    assert "http://" not in script.text


def test_static_ui_does_not_break_api_routes(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
