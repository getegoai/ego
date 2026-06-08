"""Command-line tools for local Ego Data Core workflows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, TextIO

from ego_data_core.audit import list_audit_logs
from ego_data_core.brief import DailyBriefService, daily_brief_to_dict
from ego_data_core.connectors.documents import DocumentParser
from ego_data_core.connectors.filesystem import FilesystemScanner
from ego_data_core.connectors.screen import ScreenCaptureService, screenshot_capture_to_dict
from ego_data_core.connectors.source_service import SourceService, source_to_dict
from ego_data_core.kernel.time import local_date_bounds_as_utc, normalize_report_date
from ego_data_core.nightshift import NightShiftQueue, NightShiftWorker
from ego_data_core.storage.db import get_connection, run_migrations
from ego_data_core.twin import EnhancementService, register_enhancement_handlers
from ego_data_core.workgraph import ProjectDiscoveryService, WorkItemExtractor


def main() -> None:
    raise SystemExit(run())


def run(
    argv: list[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help(out)
        return 0

    try:
        payload = args.handler(args)
    except Exception as exc:
        print(f"error: {exc}", file=err)
        return 1

    if payload is not None:
        _print_json(payload, out)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ego",
        description="Local Ego Data Core workflow CLI.",
    )
    subparsers = parser.add_subparsers(dest="command")

    init_db = subparsers.add_parser("init-db", help="Initialize the local database.")
    init_db.set_defaults(handler=_cmd_init_db)

    source = subparsers.add_parser("source", help="Manage data sources.")
    source_subparsers = source.add_subparsers(dest="source_command", required=True)
    source_add = source_subparsers.add_parser("add", help="Add a filesystem source.")
    source_add.add_argument("path", help="Local directory to scan.")
    source_add.add_argument("--name", help="Source display name.")
    source_add.add_argument(
        "--privacy-level",
        choices=["public", "private", "sensitive", "critical"],
        default="private",
    )
    source_add.add_argument("--include-glob", action="append", dest="include_globs")
    source_add.add_argument("--exclude-glob", action="append", dest="exclude_globs")
    source_add.add_argument("--max-depth", type=int)
    source_add.set_defaults(handler=_cmd_source_add)

    source_list = source_subparsers.add_parser("list", help="List configured sources.")
    source_list.set_defaults(handler=_cmd_source_list)

    scan = subparsers.add_parser("scan", help="Scan and parse a filesystem source.")
    scan.add_argument("source_id")
    scan.add_argument("--parse-limit", type=int)
    scan.set_defaults(handler=_cmd_scan)

    screen = subparsers.add_parser("screen", help="Import manual screenshots.")
    screen_subparsers = screen.add_subparsers(dest="screen_command", required=True)
    screen_import = screen_subparsers.add_parser(
        "import",
        help="Import an existing image as screenshot evidence.",
    )
    screen_import.add_argument("image_path")
    screen_import.add_argument("--source-id", required=True)
    screen_import.add_argument("--active-window")
    screen_import.add_argument("--app-name")
    screen_import.set_defaults(handler=_cmd_screen_import)

    enhance = subparsers.add_parser("enhance", help="Enhance evidence for a date.")
    enhance.add_argument("--date", dest="report_date")
    enhance.add_argument("--type", choices=["summary", "tag"], default="tag")
    enhance.add_argument(
        "--strategy",
        choices=["auto", "local_only", "external_allowed"],
        default="auto",
    )
    enhance.set_defaults(handler=_cmd_enhance)

    brief = subparsers.add_parser("brief", help="Generate or inspect briefs.")
    brief_subparsers = brief.add_subparsers(dest="brief_command", required=True)
    brief_daily = brief_subparsers.add_parser("daily", help="Generate a Daily Brief.")
    brief_daily.add_argument("--date", dest="report_date")
    brief_daily.add_argument("--force", action="store_true")
    brief_daily.add_argument("--skip-workgraph", action="store_true")
    brief_daily.set_defaults(handler=_cmd_brief_daily)

    audit = subparsers.add_parser("audit", help="Inspect audit logs.")
    audit_subparsers = audit.add_subparsers(dest="audit_command", required=True)
    audit_tail = audit_subparsers.add_parser("tail", help="Show recent audit events.")
    audit_tail.add_argument("--limit", type=int, default=20)
    audit_tail.add_argument("--event-type")
    audit_tail.set_defaults(handler=_cmd_audit_tail)

    return parser


def _cmd_init_db(_args: argparse.Namespace) -> dict[str, Any]:
    result = run_migrations()
    return {
        "database_path": str(result.database_path),
        "applied": list(result.applied),
        "skipped": list(result.skipped),
    }


def _cmd_source_add(args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.path).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        raise ValueError(f"Source path must be an existing directory: {path}")
    scan_policy: dict[str, Any] = {}
    if args.include_globs:
        scan_policy["include_globs"] = args.include_globs
    if args.exclude_globs:
        scan_policy["exclude_globs"] = args.exclude_globs
    if args.max_depth is not None:
        scan_policy["max_depth"] = args.max_depth

    source = SourceService().create_source(
        source_type="filesystem",
        name=args.name or path.name or str(path),
        root_uri=str(path),
        privacy_level=args.privacy_level,
        scan_policy=scan_policy,
    )
    return source_to_dict(source)


def _cmd_source_list(_args: argparse.Namespace) -> dict[str, Any]:
    return SourceService().list_sources()


def _cmd_scan(args: argparse.Namespace) -> dict[str, Any]:
    scan_result = FilesystemScanner().scan_source(args.source_id)
    parse_results = DocumentParser().parse_unparsed_versions(limit=args.parse_limit)
    return {
        "source_id": scan_result.source_id,
        "root_path": str(scan_result.root_path),
        "scanned_count": scan_result.scanned_count,
        "created_count": scan_result.created_count,
        "updated_count": scan_result.updated_count,
        "skipped_count": scan_result.skipped_count,
        "evidence_count": scan_result.evidence_count,
        "parsed_count": sum(1 for item in parse_results if item.status == "succeeded"),
        "parse_failed_count": sum(1 for item in parse_results if item.status == "failed"),
    }


def _cmd_screen_import(args: argparse.Namespace) -> dict[str, Any]:
    record = ScreenCaptureService().import_image_file(
        source_id=args.source_id,
        image_path=args.image_path,
        active_window=args.active_window,
        app_name=args.app_name,
    )
    return screenshot_capture_to_dict(record)


def _cmd_enhance(args: argparse.Namespace) -> dict[str, Any]:
    target_date = _normalize_date(args.report_date)
    evidence_ids = _evidence_ids_for_date(target_date)
    if not evidence_ids:
        return {
            "report_date": target_date,
            "enhancement_type": args.type,
            "job": None,
            "message": "No evidence found for date.",
        }

    queue = NightShiftQueue()
    service = EnhancementService(queue=queue)
    job = service.create_enhancement_job(
        evidence_ids=evidence_ids,
        enhancement_type=args.type,
        strategy=args.strategy,
    )
    worker = NightShiftWorker(queue, poll_interval_seconds=0)
    register_enhancement_handlers(worker, service)
    worker.run_once()
    completed = queue.get_job(job.job_id)
    return {
        "report_date": target_date,
        "enhancement_type": args.type,
        "evidence_ids": evidence_ids,
        "job": _job_to_dict(completed),
    }


def _cmd_brief_daily(args: argparse.Namespace) -> dict[str, Any]:
    target_date = _normalize_date(args.report_date)
    if not args.skip_workgraph:
        projects = ProjectDiscoveryService().discover_projects()
        work_items = WorkItemExtractor().extract_items()
    else:
        projects = {"skipped": True}
        work_items = {"skipped": True}

    brief = DailyBriefService().generate_daily_brief(
        target_date,
        force_regenerate=args.force,
    )
    payload = daily_brief_to_dict(brief)
    payload["workgraph_refresh"] = {
        "projects": projects,
        "work_items": work_items,
    }
    return payload


def _cmd_audit_tail(args: argparse.Namespace) -> dict[str, Any]:
    return list_audit_logs(
        limit=args.limit,
        event_type=args.event_type,
    )


def _evidence_ids_for_date(target_date: str) -> list[str]:
    start, end = _date_bounds(target_date)
    run_migrations()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT evidence_id
            FROM evidence
            WHERE captured_at >= ? AND captured_at < ?
            ORDER BY captured_at ASC, evidence_id ASC
            """,
            (start, end),
        ).fetchall()
    return [row["evidence_id"] for row in rows]


def _job_to_dict(job) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "job_type": job.job_type,
        "status": job.status,
        "input": job.input,
        "output": job.output,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def _normalize_date(value: str | None) -> str:
    return normalize_report_date(value)


def _date_bounds(value: str) -> tuple[str, str]:
    return local_date_bounds_as_utc(value)


def _print_json(payload: Any, out: TextIO) -> None:
    out.write(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    out.write("\n")


if __name__ == "__main__":
    main()
