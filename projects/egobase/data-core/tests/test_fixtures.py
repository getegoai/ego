from pathlib import Path

from fastapi.testclient import TestClient


def test_tmp_data_home_is_isolated(tmp_data_home: Path) -> None:
    assert tmp_data_home.name == "ego_data_home"
    assert tmp_data_home != (Path.home() / ".ego_data_core").resolve()


def test_db_path_fixture_points_inside_tmp_data_home(
    tmp_data_home: Path,
    db_path: Path,
) -> None:
    assert db_path == tmp_data_home / "db" / "ego_data_core.sqlite"


def test_migrated_db_path_creates_database(migrated_db_path: Path) -> None:
    assert migrated_db_path.exists()


def test_client_fixture_reuses_local_app(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["database"]["status"] == "ok"


def test_sample_workspace_fixture_provides_text_samples(
    sample_workspace: Path,
    sample_documents: dict[str, Path | None],
) -> None:
    assert sample_workspace.exists()
    assert sample_documents["txt"] is not None
    assert sample_documents["md"] is not None
    assert sample_documents["txt"].read_text(encoding="utf-8").startswith("Ego")
    assert "# Sample Project Plan" in sample_documents["md"].read_text(encoding="utf-8")
    assert sample_documents["pdf"] is None
    assert sample_documents["docx"] is None
