"""Privacy policy decisions for model/context/action use."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ego_data_core.audit import append_audit_log


PRIVACY_ORDER = {
    "public": 0,
    "private": 1,
    "sensitive": 2,
    "critical": 3,
}
EXTERNAL_ACTION_TYPES = frozenset(
    {
        "external_action",
        "external_model",
        "external_model_call",
        "operator_action",
    }
)


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    privacy_level: str
    reason: str | None = None
    requires_authorization: bool = False
    audit_id: str | None = None

    def __bool__(self) -> bool:
        return self.allowed


def can_use_external_model(
    privacy_level: str,
    policy: Mapping[str, Any] | None = None,
    *,
    purpose: str = "model_call",
    subject_type: str = "model_invocation",
    subject_id: str | None = None,
    database_path: str | Path | None = None,
    audit_block: bool = True,
) -> PolicyDecision:
    normalized = normalize_privacy_level(privacy_level)
    normalized_policy = dict(policy or {})
    if normalized == "public":
        return _allow(normalized)
    if normalized == "private":
        if bool(normalized_policy.get("allow_external")):
            return _allow(normalized)
        return _block(
            normalized,
            "private data cannot use external models unless allow_external policy is explicit",
            purpose=purpose,
            subject_type=subject_type,
            subject_id=subject_id,
            database_path=database_path,
            audit_block=audit_block,
        )
    if normalized == "sensitive":
        if bool(normalized_policy.get("allow_external")):
            return _allow(normalized)
        return _block(
            normalized,
            "sensitive data cannot use external models unless allow_external is explicit",
            purpose=purpose,
            subject_type=subject_type,
            subject_id=subject_id,
            database_path=database_path,
            audit_block=audit_block,
        )
    if _has_per_call_authorization(normalized_policy):
        return _allow(normalized)
    return _block(
        normalized,
        "critical data cannot use external models without per-call authorization",
        purpose=purpose,
        subject_type=subject_type,
        subject_id=subject_id,
        database_path=database_path,
        audit_block=audit_block,
        requires_authorization=True,
    )


def can_include_evidence_in_context(
    privacy_level: str,
    policy: Mapping[str, Any] | None = None,
    *,
    purpose: str = "context_build",
    subject_type: str = "evidence",
    subject_id: str | None = None,
    database_path: str | Path | None = None,
    audit_block: bool = True,
) -> PolicyDecision:
    normalized = normalize_privacy_level(privacy_level)
    normalized_policy = dict(policy or {})
    if normalized in {"public", "private", "sensitive"}:
        return _allow(normalized)
    if _has_per_call_authorization(normalized_policy):
        return _allow(normalized)
    return _block(
        normalized,
        "critical evidence cannot be included in model context without per-call authorization",
        purpose=purpose,
        subject_type=subject_type,
        subject_id=subject_id,
        database_path=database_path,
        audit_block=audit_block,
        requires_authorization=True,
    )


def requires_authorization(
    privacy_level: str,
    policy: Mapping[str, Any] | None = None,
    *,
    action_type: str = "model_call",
) -> bool:
    normalized = normalize_privacy_level(privacy_level)
    normalized_policy = dict(policy or {})
    if _has_per_call_authorization(normalized_policy):
        return False
    if normalized == "critical":
        return True
    if normalized == "sensitive" and action_type in EXTERNAL_ACTION_TYPES:
        return not bool(normalized_policy.get("allow_external"))
    if normalized == "private" and action_type in EXTERNAL_ACTION_TYPES:
        return not bool(normalized_policy.get("allow_external"))
    return False


def normalize_privacy_level(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in PRIVACY_ORDER:
        allowed = ", ".join(PRIVACY_ORDER)
        raise ValueError(f"Invalid privacy_level '{value}'. Allowed: {allowed}")
    return normalized


def effective_privacy_level(values: list[str]) -> str:
    if not values:
        return "private"
    normalized = [normalize_privacy_level(value) for value in values]
    return max(normalized, key=lambda item: PRIVACY_ORDER[item])


def _allow(privacy_level: str) -> PolicyDecision:
    return PolicyDecision(allowed=True, privacy_level=privacy_level)


def _block(
    privacy_level: str,
    reason: str,
    *,
    purpose: str,
    subject_type: str,
    subject_id: str | None,
    database_path: str | Path | None,
    audit_block: bool,
    requires_authorization: bool = False,
) -> PolicyDecision:
    audit_id = None
    if audit_block:
        record = append_audit_log(
            "policy_blocked",
            actor="system",
            target={"type": subject_type, "id": subject_id},
            payload={
                "purpose": purpose,
                "privacy_level": privacy_level,
                "reason": reason,
                "requires_authorization": requires_authorization,
            },
            database_path=database_path,
        )
        audit_id = record.audit_id
    return PolicyDecision(
        allowed=False,
        privacy_level=privacy_level,
        reason=reason,
        requires_authorization=requires_authorization,
        audit_id=audit_id,
    )


def _has_per_call_authorization(policy: Mapping[str, Any]) -> bool:
    authorization = policy.get("authorization")
    if isinstance(authorization, Mapping):
        return (
            authorization.get("scope") == "per_call"
            and bool(authorization.get("authorization_id") or authorization.get("id"))
        )
    return bool(policy.get("per_call_authorization_id"))
