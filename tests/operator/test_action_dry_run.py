from pathlib import Path

from ego_data_core.connectors.documents import DocumentParser
from ego_data_core.connectors.filesystem import FilesystemScanner
from ego_data_core.connectors.source_service import SourceService
from ego_data_core.operator import OperatorBridge
from ego_data_core.storage.db import get_connection
from ego_data_core.workgraph import AutomationOpportunityService


def test_action_plan_requires_authorization_before_dry_run(tmp_path: Path) -> None:
    automation_id = _prepare_duplicate_automation(tmp_path)
    bridge = OperatorBridge()

    action = bridge.propose_action(automation_id)

    assert action["action_id"].startswith("act_")
    assert action["status"] == "proposed"
    assert action["requires_authorization"] is True
    assert action["risk_level"] == "high"
    assert action["plan"]["dry_run_only"] is True
    assert len(action["steps"]) == 4

    blocked = bridge.execute_action(action["action_id"])

    assert blocked["status"] == "requires_authorization"
    assert blocked["requires_authorization"] is True
    assert blocked["dry_run"] is True
    assert blocked["dry_run_steps"]

    authorized = bridge.authorize_action(action["action_id"])
    assert authorized["status"] == "authorized"
    assert authorized["authorization_id"].startswith("act_")

    executed = bridge.execute_action(action["action_id"])

    assert executed["status"] == "dry_run_completed"
    assert executed["dry_run"] is True
    assert executed["risk_level"] == "high"
    assert "No computer action was executed" in _step_outputs(action["action_id"])[0]

    with get_connection() as connection:
        events = [
            row["event_type"]
            for row in connection.execute(
                "SELECT event_type FROM audit_logs ORDER BY rowid ASC"
            ).fetchall()
        ]

    assert "action_proposed" in events
    assert "action_execute_blocked" in events
    assert "action_authorized" in events
    assert "action_executed" in events


def test_action_api_propose_authorize_execute_dry_run(client, tmp_path: Path) -> None:
    automation_id = _prepare_duplicate_automation(tmp_path)

    proposed = client.post(
        "/api/v1/actions/propose",
        json={"automation_id": automation_id},
    )

    assert proposed.status_code == 200
    action = proposed.json()
    assert action["requires_authorization"] is True

    blocked = client.post(f"/api/v1/actions/{action['action_id']}/execute", json={})
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "requires_authorization"

    authorized = client.post(f"/api/v1/actions/{action['action_id']}/authorize", json={})
    assert authorized.status_code == 200
    assert authorized.json()["status"] == "authorized"

    executed = client.post(f"/api/v1/actions/{action['action_id']}/execute", json={})
    assert executed.status_code == 200
    payload = executed.json()
    assert payload["status"] == "dry_run_completed"
    assert payload["dry_run_steps"]
    assert payload["action"]["status"] == "succeeded"


def _prepare_duplicate_automation(tmp_path: Path) -> str:
    workspace = tmp_path / "workspace"
    (workspace / "alpha").mkdir(parents=True)
    (workspace / "archive").mkdir()
    duplicate_text = "Duplicate operator bridge notes. Next step: review before cleanup."
    (workspace / "alpha" / "notes.txt").write_text(duplicate_text, encoding="utf-8")
    (workspace / "archive" / "notes_copy.txt").write_text(
        duplicate_text,
        encoding="utf-8",
    )

    source = SourceService().create_source(
        source_type="filesystem",
        name="Operator Workspace",
        root_uri=str(workspace),
    )
    FilesystemScanner().scan_source(source.source_id)
    results = DocumentParser().parse_unparsed_versions()
    assert all(result.status == "succeeded" for result in results)
    payload = AutomationOpportunityService().discover_opportunities()
    duplicate = next(
        item
        for item in payload["items"]
        if item["pattern"]["pattern_type"] == "duplicate_files"
    )
    return duplicate["automation_id"]


def _step_outputs(action_id: str) -> list[str]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT output_json
            FROM action_steps
            WHERE action_id = ?
            ORDER BY step_order ASC
            """,
            (action_id,),
        ).fetchall()
    return [row["output_json"] for row in rows]
