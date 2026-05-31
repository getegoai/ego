"""Model router and deterministic rule-based adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any, Mapping, Protocol, Sequence

from ego_data_core.audit.service import append_audit_log
from ego_data_core.kernel.id_generator import generate_id
from ego_data_core.storage.db import get_connection, run_migrations, transaction
from ego_data_core.vault import VaultStorage, build_vault_uri


RULE_PROVIDER_ID = "provider_rule_local"
RULE_MODEL_ID = "model_rule_based_v0"
SUPPORTED_PURPOSES = frozenset(
    {"summary", "tag", "task_candidate", "risk_candidate"}
)
PRIVACY_ORDER = {
    "public": 0,
    "private": 1,
    "sensitive": 2,
    "critical": 3,
}


@dataclass(frozen=True)
class ModelInputRef:
    uri: str
    text: str
    privacy_level: str = "private"
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ModelRunResult:
    invocation_id: str
    purpose: str
    status: str
    output: dict[str, Any]
    output_ref_uri: str | None
    adapter_id: str
    model_id: str | None
    privacy_level: str
    error_message: str | None = None


class ModelAdapter(Protocol):
    adapter_id: str
    model_id: str | None
    model_runtime: str
    external_call: bool
    supported_purposes: frozenset[str]

    def run(
        self,
        purpose: str,
        input_refs: Sequence[ModelInputRef],
        policy: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        ...


class RuleBasedAdapter:
    adapter_id = "rule_based"
    model_id = RULE_MODEL_ID
    model_runtime = "rule"
    external_call = False
    supported_purposes = SUPPORTED_PURPOSES

    def run(
        self,
        purpose: str,
        input_refs: Sequence[ModelInputRef],
        policy: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        _validate_purpose(purpose, self.supported_purposes)
        text = _combined_text(input_refs)
        if purpose == "summary":
            return _summary_output(text)
        if purpose == "tag":
            return _tag_output(text)
        if purpose == "task_candidate":
            return _candidate_output(text, input_refs, TASK_CUES, "task")
        if purpose == "risk_candidate":
            return _candidate_output(text, input_refs, RISK_CUES, "risk")
        raise ValueError(f"Unsupported purpose: {purpose}")


class ModelRouter:
    def __init__(
        self,
        adapter: ModelAdapter | None = None,
        *,
        database_path: str | Path | None = None,
        storage: VaultStorage | None = None,
    ) -> None:
        self.adapter = adapter or RuleBasedAdapter()
        self.database_path = database_path
        self.storage = storage or VaultStorage()

    def run(
        self,
        purpose: str,
        input_refs: Sequence[ModelInputRef | Mapping[str, Any] | str],
        *,
        policy: Mapping[str, Any] | None = None,
        job_id: str | None = None,
        privacy_level: str | None = None,
    ) -> ModelRunResult:
        normalized_purpose = purpose.strip()
        normalized_policy = dict(policy or {})
        normalized_refs = _normalize_input_refs(input_refs)
        effective_privacy = _effective_privacy(normalized_refs, privacy_level)
        invocation_id = generate_id("mi")
        prompt_hash = _prompt_hash(normalized_purpose, normalized_refs, normalized_policy)
        started = time.perf_counter()

        run_migrations(self.database_path)
        self._ensure_adapter_model()

        blocked_reason = _policy_block_reason(
            self.adapter,
            effective_privacy,
            normalized_policy,
        )
        if blocked_reason:
            latency_ms = _elapsed_ms(started)
            self._write_invocation(
                invocation_id=invocation_id,
                purpose=normalized_purpose,
                input_refs=normalized_refs,
                output_ref_uri=None,
                prompt_hash=prompt_hash,
                input_tokens=_estimate_tokens(_combined_text(normalized_refs)),
                output_tokens=None,
                latency_ms=latency_ms,
                privacy_level=effective_privacy,
                allowed_by_policy=False,
                status="blocked",
                error_message=blocked_reason,
                job_id=job_id,
            )
            self._append_invocation_audit(
                invocation_id,
                normalized_purpose,
                "blocked",
                effective_privacy,
                blocked_reason,
            )
            append_audit_log(
                "policy_blocked",
                actor="system",
                target={"type": "model_invocation", "id": invocation_id},
                payload={
                    "purpose": normalized_purpose,
                    "adapter_id": self.adapter.adapter_id,
                    "privacy_level": effective_privacy,
                    "reason": blocked_reason,
                },
                database_path=self.database_path,
            )
            return ModelRunResult(
                invocation_id=invocation_id,
                purpose=normalized_purpose,
                status="blocked",
                output={},
                output_ref_uri=None,
                adapter_id=self.adapter.adapter_id,
                model_id=self.adapter.model_id,
                privacy_level=effective_privacy,
                error_message=blocked_reason,
            )

        try:
            _validate_purpose(normalized_purpose, self.adapter.supported_purposes)
            output = dict(
                self.adapter.run(normalized_purpose, normalized_refs, normalized_policy)
            )
            output_ref_uri = build_vault_uri("model_outputs", f"{invocation_id}.json")
            self.storage.safe_write_json(
                output_ref_uri,
                {
                    "invocation_id": invocation_id,
                    "purpose": normalized_purpose,
                    "adapter_id": self.adapter.adapter_id,
                    "model_id": self.adapter.model_id,
                    "output": output,
                },
            )
            status = "succeeded"
            error_message = None
        except Exception as exc:
            output = {}
            output_ref_uri = None
            status = "failed"
            error_message = str(exc)

        latency_ms = _elapsed_ms(started)
        self._write_invocation(
            invocation_id=invocation_id,
            purpose=normalized_purpose,
            input_refs=normalized_refs,
            output_ref_uri=output_ref_uri,
            prompt_hash=prompt_hash,
            input_tokens=_estimate_tokens(_combined_text(normalized_refs)),
            output_tokens=_estimate_tokens(_to_json(output)) if output else None,
            latency_ms=latency_ms,
            privacy_level=effective_privacy,
            allowed_by_policy=True,
            status=status,
            error_message=error_message,
            job_id=job_id,
        )
        self._append_invocation_audit(
            invocation_id,
            normalized_purpose,
            status,
            effective_privacy,
            error_message,
        )
        return ModelRunResult(
            invocation_id=invocation_id,
            purpose=normalized_purpose,
            status=status,
            output=output,
            output_ref_uri=output_ref_uri,
            adapter_id=self.adapter.adapter_id,
            model_id=self.adapter.model_id,
            privacy_level=effective_privacy,
            error_message=error_message,
        )

    def _ensure_adapter_model(self) -> None:
        if self.adapter.model_id != RULE_MODEL_ID:
            return
        now = _utc_now()
        with get_connection(self.database_path) as connection:
            with transaction(connection):
                connection.execute(
                    """
                    INSERT OR IGNORE INTO model_providers(
                      provider_id,
                      provider_type,
                      name,
                      privacy_allowed_json,
                      config_json,
                      created_at,
                      updated_at
                    )
                    VALUES (?, 'rule', 'Local Rule Provider', ?, '{}', ?, ?)
                    """,
                    (
                        RULE_PROVIDER_ID,
                        _to_json(["public", "private", "sensitive", "critical"]),
                        now,
                        now,
                    ),
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO models(
                      model_id,
                      provider_id,
                      name,
                      model_type,
                      runtime,
                      capabilities_json,
                      cost_profile_json,
                      created_at,
                      updated_at
                    )
                    VALUES (?, ?, 'RuleBasedAdapter v0', 'rule', 'rule', ?, '{}', ?, ?)
                    """,
                    (
                        RULE_MODEL_ID,
                        RULE_PROVIDER_ID,
                        _to_json(sorted(SUPPORTED_PURPOSES)),
                        now,
                        now,
                    ),
                )

    def _write_invocation(
        self,
        *,
        invocation_id: str,
        purpose: str,
        input_refs: Sequence[ModelInputRef],
        output_ref_uri: str | None,
        prompt_hash: str,
        input_tokens: int,
        output_tokens: int | None,
        latency_ms: int,
        privacy_level: str,
        allowed_by_policy: bool,
        status: str,
        error_message: str | None,
        job_id: str | None,
    ) -> None:
        first_input_uri = input_refs[0].uri if input_refs else None
        metadata = {
            "adapter_id": self.adapter.adapter_id,
            "input_refs": [_safe_ref_metadata(item) for item in input_refs],
        }
        with get_connection(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO model_invocations(
                  invocation_id,
                  model_id,
                  job_id,
                  purpose,
                  input_ref_uri,
                  output_ref_uri,
                  prompt_hash,
                  input_tokens,
                  output_tokens,
                  cost_estimate,
                  latency_ms,
                  privacy_level,
                  external_call,
                  allowed_by_policy,
                  status,
                  error_message,
                  created_at,
                  metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invocation_id,
                    self.adapter.model_id,
                    job_id,
                    purpose,
                    first_input_uri,
                    output_ref_uri,
                    prompt_hash,
                    input_tokens,
                    output_tokens,
                    latency_ms,
                    privacy_level,
                    int(bool(self.adapter.external_call)),
                    int(allowed_by_policy),
                    status,
                    error_message,
                    _utc_now(),
                    _to_json(metadata),
                ),
            )
            connection.commit()

    def _append_invocation_audit(
        self,
        invocation_id: str,
        purpose: str,
        status: str,
        privacy_level: str,
        error_message: str | None,
    ) -> None:
        append_audit_log(
            "model_invoked",
            actor="system",
            target={"type": "model_invocation", "id": invocation_id},
            payload={
                "purpose": purpose,
                "status": status,
                "adapter_id": self.adapter.adapter_id,
                "model_id": self.adapter.model_id,
                "privacy_level": privacy_level,
                "external_call": bool(self.adapter.external_call),
                "error": error_message,
            },
            database_path=self.database_path,
        )


TASK_CUES = (
    "todo",
    "task",
    "need to",
    "must",
    "should",
    "next step",
    "action",
    "follow up",
    "deadline",
    "\u9700\u8981",
    "\u5f85",
    "\u4e0b\u4e00\u6b65",
)
RISK_CUES = (
    "risk",
    "blocker",
    "blocked",
    "uncertain",
    "issue",
    "problem",
    "failure",
    "fail",
    "missing",
    "\u98ce\u9669",
    "\u95ee\u9898",
    "\u4e0d\u786e\u5b9a",
    "\u963b\u585e",
)
STOP_WORDS = frozenset(
    {
        "about",
        "after",
        "again",
        "also",
        "and",
        "are",
        "because",
        "but",
        "can",
        "data",
        "for",
        "from",
        "has",
        "have",
        "into",
        "not",
        "that",
        "the",
        "this",
        "with",
        "you",
        "your",
    }
)


def _normalize_input_refs(
    input_refs: Sequence[ModelInputRef | Mapping[str, Any] | str],
) -> list[ModelInputRef]:
    normalized: list[ModelInputRef] = []
    for index, item in enumerate(input_refs):
        if isinstance(item, ModelInputRef):
            normalized.append(item)
        elif isinstance(item, str):
            normalized.append(ModelInputRef(uri=f"inline://{index}", text=item))
        else:
            uri = str(item.get("uri") or item.get("input_ref_uri") or f"inline://{index}")
            text = str(item.get("text") or "")
            privacy_level = str(item.get("privacy_level") or "private")
            metadata = dict(item.get("metadata") or {})
            normalized.append(
                ModelInputRef(
                    uri=uri,
                    text=text,
                    privacy_level=_normalize_privacy_level(privacy_level),
                    metadata=metadata,
                )
            )
    if not normalized:
        raise ValueError("input_refs must not be empty")
    return normalized


def _effective_privacy(
    input_refs: Sequence[ModelInputRef],
    privacy_level: str | None,
) -> str:
    candidates = [item.privacy_level for item in input_refs]
    if privacy_level:
        candidates.append(_normalize_privacy_level(privacy_level))
    return max(candidates, key=lambda item: PRIVACY_ORDER[item])


def _normalize_privacy_level(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in PRIVACY_ORDER:
        allowed = ", ".join(PRIVACY_ORDER)
        raise ValueError(f"Invalid privacy_level '{value}'. Allowed: {allowed}")
    return normalized


def _policy_block_reason(
    adapter: ModelAdapter,
    privacy_level: str,
    policy: Mapping[str, Any],
) -> str | None:
    allow_external = bool(policy.get("allow_external"))
    if (
        adapter.external_call
        and privacy_level in {"sensitive", "critical"}
        and not allow_external
    ):
        return f"{privacy_level} data cannot use external models without explicit policy"
    return None


def _validate_purpose(purpose: str, supported_purposes: frozenset[str]) -> None:
    if purpose not in supported_purposes:
        allowed = ", ".join(sorted(supported_purposes))
        raise ValueError(f"Unsupported purpose '{purpose}'. Allowed: {allowed}")


def _combined_text(input_refs: Sequence[ModelInputRef]) -> str:
    return "\n\n".join(item.text.strip() for item in input_refs if item.text.strip())


def _summary_output(text: str) -> dict[str, Any]:
    sentences = _sentences(text)
    highlights = sentences[:3]
    summary = " ".join(highlights)
    if len(summary) > 420:
        summary = f"{summary[:417].rstrip()}..."
    return {
        "summary": summary,
        "highlights": highlights,
        "confidence": 0.45 if summary else 0.0,
        "method": "rule_based",
    }


def _tag_output(text: str) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text.lower()):
        if token in STOP_WORDS:
            continue
        counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return {
        "tags": [token for token, _count in ranked[:8]],
        "confidence": 0.4 if ranked else 0.0,
        "method": "rule_based",
    }


def _candidate_output(
    text: str,
    input_refs: Sequence[ModelInputRef],
    cues: Sequence[str],
    candidate_type: str,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    first_ref = input_refs[0].uri
    for index, sentence in enumerate(_sentences(text)):
        lowered = sentence.lower()
        matched = [cue for cue in cues if cue in lowered]
        if not matched:
            continue
        candidates.append(
            {
                "type": candidate_type,
                "title": _shorten(sentence, 160),
                "confidence": 0.5,
                "matched_cues": matched[:3],
                "source_ref": first_ref,
                "sentence_index": index,
            }
        )
    return {
        "candidates": candidates,
        "confidence": 0.5 if candidates else 0.0,
        "method": "rule_based",
    }


def _sentences(text: str) -> list[str]:
    cleaned = " ".join(text.split())
    parts = re.split(r"(?<=[.!?\u3002\uff01\uff1f])\s+|[\n\r]+", cleaned)
    return [part.strip(" -\t") for part in parts if part.strip(" -\t")]


def _shorten(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3].rstrip()}..."


def _prompt_hash(
    purpose: str,
    input_refs: Sequence[ModelInputRef],
    policy: Mapping[str, Any],
) -> str:
    payload = {
        "purpose": purpose,
        "input_refs": [
            {
                "uri": item.uri,
                "text_hash": hashlib.sha256(item.text.encode("utf-8")).hexdigest(),
                "privacy_level": item.privacy_level,
            }
            for item in input_refs
        ],
        "policy": dict(policy),
    }
    return hashlib.sha256(_to_json(payload).encode("utf-8")).hexdigest()


def _safe_ref_metadata(input_ref: ModelInputRef) -> dict[str, Any]:
    return {
        "uri": input_ref.uri,
        "privacy_level": input_ref.privacy_level,
        "metadata": input_ref.metadata or {},
    }


def _estimate_tokens(text: str) -> int:
    words = text.split()
    if words:
        return len(words)
    return max(0, len(text) // 4)


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


def _to_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
