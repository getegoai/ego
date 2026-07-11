import json

from ego_data_core.model_router import ModelInputRef, ModelRouter
from ego_data_core.storage.db import get_connection
from ego_data_core.vault import VaultStorage


def test_summary_run_writes_model_invocation_output_and_audit() -> None:
    router = ModelRouter()
    input_ref = {
        "uri": "chunk://chk_summary",
        "text": (
            "Build local evidence storage. "
            "Keep original files untouched. "
            "Generate a daily brief from verified evidence."
        ),
        "privacy_level": "private",
    }

    result = router.run("summary", [input_ref])

    assert result.status == "succeeded"
    assert result.invocation_id.startswith("mi_")
    assert result.output_ref_uri == f"vault://model_outputs/{result.invocation_id}.json"
    assert "Build local evidence storage" in result.output["summary"]

    output_payload = json.loads(VaultStorage().read_text(result.output_ref_uri))
    assert output_payload["invocation_id"] == result.invocation_id
    assert output_payload["output"]["summary"] == result.output["summary"]

    with get_connection() as connection:
        invocation = connection.execute(
            "SELECT * FROM model_invocations WHERE invocation_id = ?",
            (result.invocation_id,),
        ).fetchone()
        model = connection.execute(
            "SELECT * FROM models WHERE model_id = ?",
            (result.model_id,),
        ).fetchone()
        audit_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM audit_logs
            WHERE event_type = 'model_invoked'
              AND subject_id = ?
            """,
            (result.invocation_id,),
        ).fetchone()[0]

    assert invocation["purpose"] == "summary"
    assert invocation["status"] == "succeeded"
    assert invocation["input_ref_uri"] == "chunk://chk_summary"
    assert invocation["output_ref_uri"] == result.output_ref_uri
    assert invocation["external_call"] == 0
    assert invocation["allowed_by_policy"] == 1
    assert invocation["prompt_hash"]
    assert model["model_type"] == "rule"
    assert audit_count == 1


def test_rule_based_adapter_supports_tags_tasks_and_risks() -> None:
    router = ModelRouter()
    refs = [
        ModelInputRef(
            uri="chunk://chk_work",
            text=(
                "Evidence storage should preserve local files. "
                "Next step: create the parser task for daily brief generation. "
                "Risk: parsing failure could hide an important issue."
            ),
        )
    ]

    tags = router.run("tag", refs).output["tags"]
    tasks = router.run("task_candidate", refs).output["candidates"]
    risks = router.run("risk_candidate", refs).output["candidates"]

    assert "evidence" in tags
    assert any("Next step" in item["title"] for item in tasks)
    assert any("Risk:" in item["title"] for item in risks)


def test_sensitive_data_blocks_external_adapter_by_default() -> None:
    adapter = _ExternalAdapter()
    router = ModelRouter(adapter=adapter)

    result = router.run(
        "summary",
        [
            {
                "uri": "chunk://chk_sensitive",
                "text": "Sensitive project note",
                "privacy_level": "sensitive",
            }
        ],
    )

    assert result.status == "blocked"
    assert result.output == {}
    assert result.output_ref_uri is None
    assert "cannot use external models" in result.error_message
    assert adapter.called is False

    with get_connection() as connection:
        invocation = connection.execute(
            "SELECT * FROM model_invocations WHERE invocation_id = ?",
            (result.invocation_id,),
        ).fetchone()
        policy_blocked_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM audit_logs
            WHERE event_type = 'policy_blocked'
              AND subject_id = ?
            """,
            (result.invocation_id,),
        ).fetchone()[0]

    assert invocation["status"] == "blocked"
    assert invocation["external_call"] == 1
    assert invocation["allowed_by_policy"] == 0
    assert policy_blocked_count == 1


def test_critical_data_blocks_rule_based_context_without_authorization() -> None:
    result = ModelRouter().run(
        "summary",
        [
            {
                "uri": "chunk://chk_critical",
                "text": "Critical project note",
                "privacy_level": "critical",
            }
        ],
    )

    assert result.status == "blocked"
    assert "critical evidence cannot be included" in result.error_message
    with get_connection() as connection:
        invocation = connection.execute(
            "SELECT * FROM model_invocations WHERE invocation_id = ?",
            (result.invocation_id,),
        ).fetchone()
        policy_blocked_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM audit_logs
            WHERE event_type = 'policy_blocked'
              AND subject_id = ?
            """,
            (result.invocation_id,),
        ).fetchone()[0]

    assert invocation["status"] == "blocked"
    assert invocation["external_call"] == 0
    assert invocation["allowed_by_policy"] == 0
    assert policy_blocked_count == 1


def test_explicit_policy_can_allow_external_sensitive_run() -> None:
    adapter = _ExternalAdapter()
    router = ModelRouter(adapter=adapter)

    result = router.run(
        "summary",
        [{"uri": "chunk://chk_allowed", "text": "Allowed external summary input"}],
        privacy_level="sensitive",
        policy={"allow_external": True},
    )

    assert result.status == "succeeded"
    assert result.output["summary"] == "external summary"
    assert adapter.called is True

    with get_connection() as connection:
        invocation = connection.execute(
            "SELECT * FROM model_invocations WHERE invocation_id = ?",
            (result.invocation_id,),
        ).fetchone()

    assert invocation["external_call"] == 1
    assert invocation["allowed_by_policy"] == 1
    assert invocation["privacy_level"] == "sensitive"


def test_unsupported_purpose_is_recorded_as_failed_invocation() -> None:
    result = ModelRouter().run(
        "unknown_purpose",
        [{"uri": "chunk://chk_unknown", "text": "Some input"}],
    )

    assert result.status == "failed"
    assert "Unsupported purpose" in result.error_message

    with get_connection() as connection:
        invocation = connection.execute(
            "SELECT * FROM model_invocations WHERE invocation_id = ?",
            (result.invocation_id,),
        ).fetchone()

    assert invocation["status"] == "failed"
    assert invocation["error_message"] == result.error_message


class _ExternalAdapter:
    adapter_id = "external_test"
    model_id = None
    model_runtime = "external"
    external_call = True
    supported_purposes = frozenset({"summary"})

    def __init__(self) -> None:
        self.called = False

    def run(self, purpose, input_refs, policy):
        self.called = True
        return {
            "summary": "external summary",
            "purpose": purpose,
            "ref_count": len(input_refs),
            "policy": dict(policy),
        }
