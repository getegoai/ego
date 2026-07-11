"""Stable application errors and API error responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import uuid


@dataclass(frozen=True)
class ErrorPayload:
    code: str
    message: str
    request_id: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "request_id": self.request_id,
        }
        if self.details:
            payload["details"] = self.details
        return payload


class EgoError(Exception):
    code = "ego_error"
    status_code = 500
    default_message = "Ego Data Core error"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = dict(details or {})
        super().__init__(self.message)

    def to_payload(self, request_id: str) -> ErrorPayload:
        return ErrorPayload(
            code=self.code,
            message=self.message,
            request_id=request_id,
            details=self.details or None,
        )


class PolicyBlockedError(EgoError):
    code = "policy_blocked"
    status_code = 403
    default_message = "Action blocked by policy"


class NotFoundError(EgoError):
    code = "not_found"
    status_code = 404
    default_message = "Resource not found"


class ValidationError(EgoError):
    code = "validation_error"
    status_code = 400
    default_message = "Validation failed"


class ConnectorError(EgoError):
    code = "connector_error"
    status_code = 502
    default_message = "Connector failed"


class ModelError(EgoError):
    code = "model_error"
    status_code = 502
    default_message = "Model operation failed"


class StorageError(EgoError):
    code = "storage_error"
    status_code = 500
    default_message = "Storage operation failed"


def request_id_from_headers(headers: Mapping[str, str]) -> str:
    incoming = headers.get("x-request-id") or headers.get("X-Request-ID")
    if incoming and incoming.strip():
        return incoming.strip()[:128]
    return f"req_{uuid.uuid4().hex}"


def error_payload(exc: EgoError, request_id: str) -> dict[str, Any]:
    return exc.to_payload(request_id).to_dict()


def validation_error_from_exception(exc: Exception) -> ValidationError:
    return ValidationError(str(exc) or "Validation failed")
