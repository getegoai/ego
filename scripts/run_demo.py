"""Run the local Ego Data Core demo loop."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from io import StringIO
import json
import os
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
DEFAULT_WORKSPACE = REPO_ROOT / "demo" / "sample_workspace"


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.exists() or not workspace.is_dir():
        print(f"error: demo workspace does not exist: {workspace}", file=sys.stderr)
        return 1

    if args.data_home:
        os.environ["EGO_DATA_HOME"] = str(Path(args.data_home).expanduser().resolve())
    else:
        os.environ.setdefault("EGO_DATA_HOME", str((REPO_ROOT / ".ego_demo_home").resolve()))
    os.environ.setdefault("EGO_PROFILE", "dev")
    sys.path.insert(0, str(SRC_DIR))

    try:
        summary = run_demo(
            workspace,
            report_date=args.report_date or _today_utc(),
            enhancement_type=args.enhancement_type,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


def run_demo(
    workspace: Path,
    *,
    report_date: str,
    enhancement_type: str = "tag",
) -> dict[str, Any]:
    from ego_data_core.cli import run as cli_run
    from ego_data_core.vault import VaultStorage

    init_db = _run_cli(cli_run, ["init-db"])
    source = _run_cli(
        cli_run,
        [
            "source",
            "add",
            str(workspace),
            "--name",
            "Ego Demo Workspace",
            "--privacy-level",
            "private",
        ],
    )
    scan = _run_cli(cli_run, ["scan", source["source_id"]])
    enhance = _run_cli(
        cli_run,
        ["enhance", "--date", report_date, "--type", enhancement_type],
    )
    brief = _run_cli(
        cli_run,
        ["brief", "daily", "--date", report_date, "--force"],
    )
    audit = _run_cli(
        cli_run,
        ["audit", "tail", "--event-type", "brief_generated", "--limit", "5"],
    )

    markdown_uri = brief["metadata"]["markdown_uri"]
    markdown_path = VaultStorage().resolve_uri(markdown_uri)
    return {
        "database_path": init_db["database_path"],
        "workspace": str(workspace),
        "source_id": source["source_id"],
        "report_date": report_date,
        "scan": scan,
        "enhance": enhance,
        "report_id": brief["report_id"],
        "markdown_uri": markdown_uri,
        "markdown_path": str(markdown_path),
        "audit_total": audit["total"],
    }


def _run_cli(cli_run, argv: list[str]) -> dict[str, Any]:
    stdout = StringIO()
    stderr = StringIO()
    status = cli_run(argv, stdout=stdout, stderr=stderr)
    if status != 0:
        raise RuntimeError(stderr.getvalue().strip() or f"command failed: {' '.join(argv)}")
    text = stdout.getvalue().strip()
    return json.loads(text) if text else {}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Ego Data Core demo loop.")
    parser.add_argument(
        "--workspace",
        default=str(DEFAULT_WORKSPACE),
        help="Demo workspace directory.",
    )
    parser.add_argument("--date", dest="report_date", help="Brief date, YYYY-MM-DD.")
    parser.add_argument(
        "--enhancement-type",
        choices=["summary", "tag"],
        default="tag",
    )
    parser.add_argument("--data-home", help="Override EGO_DATA_HOME for the demo run.")
    return parser


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
