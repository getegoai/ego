from collections.abc import Iterator
from pathlib import Path
import shutil

from fastapi.testclient import TestClient
import pytest

from ego_data_core.api.app import create_app
from ego_data_core.storage.db import run_migrations


@pytest.fixture
def tmp_data_home(tmp_path: Path) -> Path:
    return tmp_path / "ego_data_home"


@pytest.fixture(autouse=True)
def isolated_ego_environment(
    tmp_data_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    monkeypatch.setenv("EGO_DATA_HOME", str(tmp_data_home))
    monkeypatch.setenv("EGO_PROFILE", "test")
    yield


@pytest.fixture
def db_path(tmp_data_home: Path) -> Path:
    return tmp_data_home / "db" / "ego_data_core.sqlite"


@pytest.fixture
def migrated_db_path(db_path: Path) -> Path:
    run_migrations(db_path)
    return db_path


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_workspace(tmp_path: Path) -> Path:
    source = Path(__file__).parent / "fixtures" / "sample_workspace"
    target = tmp_path / "sample_workspace"
    shutil.copytree(source, target)
    return target


@pytest.fixture
def sample_documents(sample_workspace: Path) -> dict[str, Path | None]:
    return {
        "txt": sample_workspace / "notes.txt",
        "md": sample_workspace / "project_plan.md",
        "pdf": None,
        "docx": None,
    }
