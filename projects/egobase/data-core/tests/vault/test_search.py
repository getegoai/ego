import json
from pathlib import Path
import sqlite3

from ego_data_core.connectors.documents import DocumentParser
from ego_data_core.connectors.filesystem import FilesystemScanner
from ego_data_core.connectors.source_service import SourceService
from ego_data_core.kernel.time import local_today
from ego_data_core.vault import LocalSearchService


def test_search_returns_fts_results_without_absolute_paths(client, tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    source_id = _make_search_workspace(workspace)

    response = client.get(
        "/api/v1/search",
        params={"q": "daily brief", "limit": 10},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["backend"] == "fts5"
    assert payload["total"] >= 1
    first = payload["items"][0]
    assert first["evidence_id"].startswith("ev_")
    assert first["chunk_id"].startswith("chk_")
    assert first["title"] == "alpha_notes.txt"
    assert first["source_id"] == source_id
    assert "daily" in first["snippet"].lower()

    serialized = json.dumps(payload, ensure_ascii=False)
    assert str(workspace) not in serialized
    assert "file:///" not in serialized


def test_search_filters_by_source_and_date_through_api(client, tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    source_id = _make_search_workspace(workspace)
    other_workspace = tmp_path / "other"
    other_workspace.mkdir()
    (other_workspace / "other.txt").write_text(
        "Daily brief from unrelated source.",
        encoding="utf-8",
    )
    other_source = SourceService().create_source(
        source_type="filesystem",
        name="Other Search Workspace",
        root_uri=str(other_workspace),
    )
    FilesystemScanner().scan_source(other_source.source_id)
    DocumentParser().parse_unparsed_versions()

    current = client.get(
        "/api/v1/search",
        params={
            "q": "daily brief",
            "source_id": source_id,
            "date_from": local_today(),
            "date_to": local_today(),
        },
    ).json()
    future = client.get(
        "/api/v1/search",
        params={
            "q": "daily brief",
            "source_id": source_id,
            "date_from": "2099-01-01",
            "date_to": "2099-01-01",
        },
    ).json()

    assert current["total"] >= 1
    assert all(item["source_id"] == source_id for item in current["items"])
    assert future["total"] == 0


def test_search_like_fallback_returns_matches(monkeypatch, tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _make_search_workspace(workspace)

    def fail_fts(*args, **kwargs):
        raise sqlite3.OperationalError("no such module: fts5")

    monkeypatch.setattr(LocalSearchService, "_search_fts", fail_fts)
    payload = LocalSearchService().search("fallback keyword")

    assert payload["backend"] == "like"
    assert payload["total"] == 1
    assert payload["items"][0]["match_type"] == "like"
    assert "[fallback]" in payload["items"][0]["snippet"].lower()


def test_search_rejects_empty_query(client) -> None:
    response = client.get("/api/v1/search", params={"q": "   "})

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def _make_search_workspace(workspace: Path) -> str:
    workspace.mkdir(parents=True)
    (workspace / "alpha_notes.txt").write_text(
        (
            "Alpha daily brief notes. "
            "The local search should find evidence chunks and return snippets. "
            "Fallback keyword appears in this same supported document."
        ),
        encoding="utf-8",
    )
    (workspace / "beta_notes.txt").write_text(
        "Beta project risk notes with unrelated content.",
        encoding="utf-8",
    )
    source = SourceService().create_source(
        source_type="filesystem",
        name="Search Workspace",
        root_uri=str(workspace),
    )
    FilesystemScanner().scan_source(source.source_id)
    results = DocumentParser().parse_unparsed_versions()
    assert all(result.status == "succeeded" for result in results)
    return source.source_id
