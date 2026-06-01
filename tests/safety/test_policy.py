from ego_data_core.safety import (
    can_include_evidence_in_context,
    can_use_external_model,
    effective_privacy_level,
    requires_authorization,
)
from ego_data_core.storage.db import get_connection


def test_public_can_use_external_model_without_policy() -> None:
    decision = can_use_external_model("public", purpose="summary")

    assert decision.allowed is True
    assert decision.reason is None


def test_private_external_model_requires_policy_and_audits_block() -> None:
    blocked = can_use_external_model(
        "private",
        purpose="summary",
        subject_type="model_invocation",
        subject_id="mi_private",
    )
    allowed = can_use_external_model(
        "private",
        {"allow_external": True},
        purpose="summary",
        subject_id="mi_private_allowed",
    )

    assert blocked.allowed is False
    assert "cannot use external models" in blocked.reason
    assert blocked.audit_id is not None
    assert allowed.allowed is True

    with get_connection() as connection:
        audit = connection.execute(
            """
            SELECT *
            FROM audit_logs
            WHERE event_type = 'policy_blocked'
              AND subject_id = 'mi_private'
            """
        ).fetchone()

    assert audit is not None


def test_sensitive_external_model_defaults_to_local_only() -> None:
    blocked = can_use_external_model(
        "sensitive",
        purpose="summary",
        subject_id="mi_sensitive",
    )
    allowed = can_use_external_model(
        "sensitive",
        {"allow_external": True},
        purpose="summary",
        subject_id="mi_sensitive_allowed",
    )

    assert blocked.allowed is False
    assert "sensitive data cannot use external models" in blocked.reason
    assert allowed.allowed is True


def test_critical_model_context_requires_per_call_authorization() -> None:
    blocked_external = can_use_external_model(
        "critical",
        {"allow_external": True},
        purpose="summary",
        subject_id="mi_critical",
    )
    blocked_context = can_include_evidence_in_context(
        "critical",
        purpose="summary",
        subject_id="ev_critical",
    )
    allowed = can_include_evidence_in_context(
        "critical",
        {"authorization": {"scope": "per_call", "authorization_id": "act_1"}},
        purpose="summary",
        subject_id="ev_critical_allowed",
    )

    assert blocked_external.allowed is False
    assert blocked_external.requires_authorization is True
    assert blocked_context.allowed is False
    assert blocked_context.requires_authorization is True
    assert allowed.allowed is True


def test_requires_authorization_and_effective_privacy() -> None:
    assert requires_authorization("critical") is True
    assert requires_authorization("sensitive", action_type="external_model") is True
    assert requires_authorization(
        "sensitive",
        {"allow_external": True},
        action_type="external_model",
    ) is False
    assert requires_authorization("public", action_type="external_model") is False
    assert effective_privacy_level(["public", "private", "critical"]) == "critical"
