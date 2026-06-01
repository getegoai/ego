from datetime import datetime, timezone

from ego_data_core.kernel.time import (
    local_date_bounds_as_utc,
    local_today,
    normalize_report_date,
)


def test_local_date_bounds_include_current_utc_instant() -> None:
    today = local_today()
    start, end = local_date_bounds_as_utc(today)
    now = datetime.now(timezone.utc).isoformat()

    assert start <= now < end


def test_normalize_report_date_defaults_to_local_today() -> None:
    before = local_today()
    value = normalize_report_date(None)
    after = local_today()

    assert value in {before, after}
    assert normalize_report_date("2026-06-01") == "2026-06-01"
