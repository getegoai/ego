"""Unified ID generation for Ego Data Core entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import re
import secrets
from typing import Final


ID_ALPHABET: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
DEFAULT_SUFFIX_LENGTH: Final[int] = 16

ALLOWED_PREFIXES: Final[frozenset[str]] = frozenset(
    {
        "usr",
        "dev",
        "src",
        "obj",
        "ver",
        "ev",
        "chk",
        "enh",
        "ent",
        "proj",
        "task",
        "q",
        "risk",
        "auto",
        "brief",
        "report",
        "item",
        "job",
        "mi",
        "act",
        "aud",
    }
)

ID_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^(?P<prefix>[a-z][a-z0-9]*)_(?P<date>\d{8})_(?P<suffix>[0-9A-Z]+)$"
)


class InvalidIdPrefixError(ValueError):
    """Raised when an ID prefix is not registered for v0.1 entities."""


@dataclass(frozen=True)
class ParsedEgoId:
    prefix: str
    date: str
    suffix: str


def generate_id(
    prefix: str,
    *,
    on_date: date | datetime | None = None,
    suffix_length: int = DEFAULT_SUFFIX_LENGTH,
) -> str:
    normalized_prefix = normalize_prefix(prefix)
    id_date = _format_date(on_date)
    suffix = _random_base32(suffix_length)
    return f"{normalized_prefix}_{id_date}_{suffix}"


def normalize_prefix(prefix: str) -> str:
    normalized = prefix.strip().lower()
    if normalized.endswith("_"):
        normalized = normalized[:-1]
    if normalized not in ALLOWED_PREFIXES:
        allowed = ", ".join(sorted(ALLOWED_PREFIXES))
        raise InvalidIdPrefixError(
            f"Unsupported Ego ID prefix '{prefix}'. Allowed prefixes: {allowed}"
        )
    return normalized


def parse_id(value: str) -> ParsedEgoId:
    match = ID_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError(f"Invalid Ego ID format: {value}")
    prefix = normalize_prefix(match.group("prefix"))
    return ParsedEgoId(
        prefix=prefix,
        date=match.group("date"),
        suffix=match.group("suffix"),
    )


def _format_date(value: date | datetime | None) -> str:
    if value is None:
        value = datetime.now(timezone.utc).date()
    elif isinstance(value, datetime):
        value = value.astimezone(timezone.utc).date() if value.tzinfo else value.date()
    return value.strftime("%Y%m%d")


def _random_base32(length: int) -> str:
    if length <= 0:
        raise ValueError("suffix_length must be positive")
    return "".join(
        ID_ALPHABET[secrets.randbelow(len(ID_ALPHABET))] for _ in range(length)
    )
