from pathlib import Path

from ego_data_core.connectors.documents import DocumentParser
from ego_data_core.connectors.filesystem import FilesystemScanner
from ego_data_core.connectors.source_service import SourceService
from ego_data_core.storage.db import get_connection
from ego_data_core.workgraph import AutomationOpportunityService


def test_discovers_duplicate_and_loose_folder_opportunities(tmp_path: Path) -> None:
    _prepare_workspace(tmp_path)

    payload = AutomationOpportunityService().discover_opportunities()

    assert payload["total"] >= 2
    by_pattern = {item["pattern"]["pattern_type"]: item for item in payload["items"]}
    duplicate = by_pattern["duplicate_files"]
    loose_folder = by_pattern["loose_folder"]

    assert duplicate["status"] == "proposed"
    assert duplicate["risk_level"] == "high"
    assert duplicate["requires_authorization"] is True
    assert duplicate["required_authorization"] == "user_confirmation_required"
    assert "delete_duplicate_files" in duplicate["pattern"]["candidate_actions"]
    assert len(duplicate["evidence_ids"]) == 2

    assert loose_folder["status"] == "proposed"
    assert loose_folder["risk_level"] == "high"
    assert loose_folder["requires_authorization"] is True
    assert len(loose_folder["evidence_ids"]) == 2

    with get_connection() as connection:
        linked = connection.execute(
            """
            SELECT COUNT(*)
            FROM graph_edges
            WHERE dst_type = 'automation'
              AND dst_id = ?
            """,
            (duplicate["automation_id"],),
        ).fetchone()[0]

    assert linked == 2


def test_discovery_is_idempotent_and_api_exposes_opportunities(client, tmp_path: Path) -> None:
    _prepare_workspace(tmp_path)
    service = AutomationOpportunityService()
    first = service.discover_opportunities()
    second = service.discover_opportunities()

    assert second["total"] == first["total"]
    assert {
        item["automation_id"] for item in second["items"]
    } == {item["automation_id"] for item in first["items"]}

    response = client.post("/api/v1/workgraph/automations/discover")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == first["total"]

    listed = client.get("/api/v1/workgraph/automations")
    assert listed.status_code == 200
    assert listed.json()["total"] == first["total"]


def _prepare_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "alpha").mkdir(parents=True)
    (workspace / "archive").mkdir()
    (workspace / "Downloads").mkdir()

    duplicate_text = "Duplicate project handoff notes. Next step: review before cleanup."
    (workspace / "alpha" / "handoff.txt").write_text(duplicate_text, encoding="utf-8")
    (workspace / "archive" / "handoff_copy.txt").write_text(
        duplicate_text,
        encoding="utf-8",
    )
    (workspace / "Downloads" / "todo.txt").write_text(
        "Download inbox item. Need classify this document before moving anything.",
        encoding="utf-8",
    )
    (workspace / "Downloads" / "risk.txt").write_text(
        "Download inbox item. Risk: loose notes may hide an unfinished task.",
        encoding="utf-8",
    )

    source = SourceService().create_source(
        source_type="filesystem",
        name="Automation Workspace",
        root_uri=str(workspace),
    )
    FilesystemScanner().scan_source(source.source_id)
    results = DocumentParser().parse_unparsed_versions()
    assert all(result.status == "succeeded" for result in results)
