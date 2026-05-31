"""Logging helpers with conservative payload redaction."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import logging
from typing import Any

from ego_data_core.kernel.errors import EgoError


SENSITIVE_KEYS = frozenset(
    {
        "body",
        "content",
        "content_json",
        "description",
        "input",
        "input_json",
        "output",
        "output_json",
        "prompt",
        "raw",
        "raw_text",
        "text",
    }
)
MAX_SAFE_STRING_LENGTH = 120


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def redact_payload(payload: Any) -> Any:
    if isinstance(payload, Mapping):
        return {
            str(key): _redact_value(str(key), value)
            for key, value in payload.items()
        }
    if isinstance(payload, list | tuple):
        return [_redact_value("", value) for value in payload]
    return _redact_value("", payload)


def safe_error_message(exc: Exception) -> str:
    if isinstance(exc, EgoError):
        return exc.message
    message = str(exc).strip()
    if not message:
        return exc.__class__.__name__
    return _truncate(message)


def log_exception(
    logger: logging.Logger,
    message: str,
    exc: Exception,
    *,
    context: Mapping[str, Any] | None = None,
) -> None:
    logger.error(
        "%s: %s",
        message,
        safe_error_message(exc),
        extra={"ego_context": redact_payload(context or {})},
    )


def _redact_value(key: str, value: Any) -> Any:
    normalized_key = key.lower()
    if normalized_key in SENSITIVE_KEYS:
        return _redacted_marker(value)
    if isinstance(value, Mapping):
        return redact_payload(value)
    if isinstance(value, list | tuple):
        return [_redact_value("", item) for item in value]
    if isinstance(value, str):
        return _truncate(value)
    return value


def _redacted_marker(value: Any) -> str:
    if isinstance(value, str):
        return f"<redacted:{len(value)} chars>"
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        return f"<redacted:{len(value)} items>"
    return "<redacted>"


def _truncate(value: str) -> str:
    collapsed = " ".join(value.split())
    if len(collapsed) <= MAX_SAFE_STRING_LENGTH:
        return collapsed
    return collapsed[: MAX_SAFE_STRING_LENGTH - 3].rstrip() + "..."
