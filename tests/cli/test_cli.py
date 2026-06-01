from io import StringIO
import json
from pathlib import Path

from ego_data_core.cli import run
from ego_data_core.kernel.time import local_today
from ego_data_core.vault import VaultStorage


def test_cli_init_db_and_source_add(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    init_status, init_payload, init_error = _run_cli(["init-db"])
    add_status, add_payload, add_error = _run_cli(
        ["source", "add", str(workspace), "--name", "CLI Workspace"]
    )

    assert init_status == 0, init_error
    assert add_status == 0, add_error
    assert Path(init_payload["database_path"]).exists()
    assert add_payload["source_type"] == "filesystem"
    assert add_payload["name"] == "CLI Workspace"
    assert add_payload["root_uri"] == str(workspace.resolve())


def test_cli_runs_scan_enhance_brief_and_audit_loop(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    project = workspace / "alpha"
    project.mkdir(parents=True)
    (project / "alpha_cli.txt").write_text(
        (
            "Alpha CLI status. "
            "Next step: create the command line demo task. "
            "Question: should the CLI refresh the work graph before brief generation? "
            "Risk: a missing command line loop could make validation hard."
        ),
        encoding="utf-8",
    )
    target_date = local_today()

    add_status, source_payload, add_error = _run_cli(
        ["source", "add", str(workspace), "--name", "CLI Loop"]
    )
    assert add_status == 0, add_error

    scan_status, scan_payload, scan_error = _run_cli(["scan", source_payload["source_id"]])
    assert scan_status == 0, scan_error
    assert scan_payload["created_count"] == 1
    assert scan_payload["parsed_count"] == 1

    enhance_status, enhance_payload, enhance_error = _run_cli(
        ["enhance", "--date", target_date, "--type", "tag"]
    )
    assert enhance_status == 0, enhance_error
    assert enhance_payload["job"]["status"] == "succeeded"

    brief_status, brief_payload, brief_error = _run_cli(
        ["brief", "daily", "--date", target_date, "--force"]
    )
    assert brief_status == 0, brief_error
    assert brief_payload["metadata"]["markdown_uri"].startswith("vault://briefs/")
    assert brief_payload["workgraph_refresh"]["projects"]["total"] >= 1
    assert brief_payload["workgraph_refresh"]["work_items"]["total"] >= 3

    markdown = VaultStorage().read_text(brief_payload["metadata"]["markdown_uri"])
    assert "alpha_cli.txt" in markdown
    assert "Evidence: [ev_" in markdown

    audit_status, audit_payload, audit_error = _run_cli(
        ["audit", "tail", "--event-type", "brief_generated"]
    )
    assert audit_status == 0, audit_error
    assert audit_payload["total"] == 1
    assert audit_payload["items"][0]["subject_id"] == brief_payload["report_id"]


def test_cli_failures_return_non_zero_and_write_stderr() -> None:
    status, payload, error = _run_cli(["scan", "src_missing"])

    assert status == 1
    assert payload is None
    assert "error:" in error


def _run_cli(argv: list[str]) -> tuple[int, dict | None, str]:
    stdout = StringIO()
    stderr = StringIO()
    status = run(argv, stdout=stdout, stderr=stderr)
    text = stdout.getvalue().strip()
    payload = json.loads(text) if text else None
    return status, payload, stderr.getvalue()
