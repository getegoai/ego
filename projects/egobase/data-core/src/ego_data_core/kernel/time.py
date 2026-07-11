"""Date helpers for local-day reporting over UTC timestamps."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone


def local_today() -> str:
    return datetime.now().astimezone().date().isoformat()


def normalize_report_date(value: str | None) -> str:
    if value is None:
        return local_today()
    return date.fromisoformat(value).isoformat()


def local_date_bounds_as_utc(value: str) -> tuple[str, str]:
    report_date = date.fromisoformat(value)
    local_tz = datetime.now().astimezone().tzinfo
    start_local = datetime.combine(report_date, time.min, tzinfo=local_tz)
    end_local = start_local + timedelta(days=1)
    return (
        start_local.astimezone(timezone.utc).isoformat(),
        end_local.astimezone(timezone.utc).isoformat(),
    )
