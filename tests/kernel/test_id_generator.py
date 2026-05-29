from datetime import date, datetime, timezone

import pytest

from ego_data_core.kernel.id_generator import (
    ALLOWED_PREFIXES,
    DEFAULT_SUFFIX_LENGTH,
    InvalidIdPrefixError,
    generate_id,
    normalize_prefix,
    parse_id,
)


REQUIRED_PREFIXES = {
    "usr",
    "dev",
    "src",
    "obj",
    "ver",
    "ev",
    "chk",
    "enh",
    "proj",
    "task",
    "q",
    "risk",
    "auto",
    "brief",
    "job",
    "mi",
    "act",
    "aud",
    "report",
    "item",
}


def test_required_prefixes_are_supported() -> None:
    assert REQUIRED_PREFIXES.issubset(ALLOWED_PREFIXES)

    generated = {
        prefix: generate_id(prefix, on_date=date(2026, 5, 29))
        for prefix in REQUIRED_PREFIXES
    }

    for prefix, ego_id in generated.items():
        assert ego_id.startswith(f"{prefix}_20260529_")
        parsed = parse_id(ego_id)
        assert parsed.prefix == prefix
        assert parsed.date == "20260529"
        assert len(parsed.suffix) == DEFAULT_SUFFIX_LENGTH


def test_prefix_normalization_accepts_trailing_underscore() -> None:
    assert normalize_prefix("ev_") == "ev"
    ego_id = generate_id("EV_", on_date=date(2026, 5, 29), suffix_length=4)

    assert ego_id.startswith("ev_20260529_")
    assert len(parse_id(ego_id).suffix) == 4


def test_datetime_input_is_formatted_as_utc_date() -> None:
    ego_id = generate_id(
        "job",
        on_date=datetime(2026, 5, 29, 23, 30, tzinfo=timezone.utc),
        suffix_length=4,
    )

    assert parse_id(ego_id).date == "20260529"


def test_invalid_prefix_raises_clear_error() -> None:
    with pytest.raises(InvalidIdPrefixError, match="Unsupported Ego ID prefix"):
        generate_id("bad")


def test_invalid_format_fails_parse() -> None:
    with pytest.raises(ValueError, match="Invalid Ego ID format"):
        parse_id("ev_not_a_valid_id")


def test_invalid_suffix_length_raises() -> None:
    with pytest.raises(ValueError, match="suffix_length must be positive"):
        generate_id("ev", suffix_length=0)


def test_generates_100k_ids_without_collision() -> None:
    ids = {generate_id("ev") for _ in range(100_000)}

    assert len(ids) == 100_000
