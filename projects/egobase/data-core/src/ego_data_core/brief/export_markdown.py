"""Markdown export for brief reports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import TYPE_CHECKING, Any, Mapping

from ego_data_core.storage.db import get_connection, run_migrations
from ego_data_core.vault import VaultStorage, build_vault_uri

if TYPE_CHECKING:
    from ego_data_core.brief.daily import DailyBriefRecord

SYSTEM_ITEM_TYPES = frozenset({"data_health", "system"})


@dataclass(frozen=True)
class EvidenceReference:
    evidence_id: str
    title: str
    path_label: str
    captured_at: str
    excerpt: str | None


class BriefMarkdownExporter:
    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        storage: VaultStorage | None = None,
    ) -> None:
        self.database_path = database_path
        self.storage = storage or VaultStorage()

    def export_report(self, report: "DailyBriefRecord") -> str:
        markdown = self.render_report(report)
        filename = _filename_for_report(report)
        uri = build_vault_uri("briefs", filename)
        return self.storage.safe_write_text(uri, markdown)

    def render_report(self, report: "DailyBriefRecord") -> str:
        evidence_refs = self._load_evidence_references(report)
        lines = [
            f"# {report.title}",
            "",
            f"Date: {report.report_date}",
            f"Status: {report.status}",
            f"Generated: {report.generated_at}",
            "",
            "## Summary",
            "",
            report.summary or "",
            "",
            "## Sections",
            "",
        ]

        for item in report.items:
            lines.extend(
                [
                    f"### {item['title']}",
                    "",
                    item.get("body") or "",
                    "",
                    f"Type: {item['item_type']}",
                    f"Severity: {item['severity']}",
                ]
            )
            confidence = item.get("confidence")
            if confidence is not None:
                lines.append(f"Confidence: {confidence:.2f}")
            lines.append("")
            lines.extend(_evidence_lines(item, evidence_refs))
            lines.append("")

        return "\n".join(lines).strip() + "\n"

    def _load_evidence_references(
        self,
        report: "DailyBriefRecord",
    ) -> dict[str, EvidenceReference]:
        evidence_ids = sorted(
            {
                evidence_id
                for item in report.items
                for evidence_id in item.get("evidence_ids", [])
            }
        )
        if not evidence_ids:
            return {}

        run_migrations(self.database_path)
        placeholders = ",".join("?" for _ in evidence_ids)
        with get_connection(self.database_path) as connection:
            rows = connection.execute(
                f"""
                SELECT
                  ev.evidence_id,
                  ev.captured_at,
                  raw.title,
                  raw.metadata_json AS raw_metadata_json,
                  chunk.text AS chunk_text
                FROM evidence ev
                JOIN raw_objects raw ON raw.raw_object_id = ev.raw_object_id
                LEFT JOIN evidence_text_chunks chunk
                  ON chunk.evidence_id = ev.evidence_id
                 AND chunk.chunk_index = 0
                WHERE ev.evidence_id IN ({placeholders})
                ORDER BY ev.evidence_id ASC
                """,
                evidence_ids,
            ).fetchall()

        result: dict[str, EvidenceReference] = {}
        for row in rows:
            metadata = json.loads(row["raw_metadata_json"])
            title = row["title"] or row["evidence_id"]
            result[row["evidence_id"]] = EvidenceReference(
                evidence_id=row["evidence_id"],
                title=title,
                path_label=_safe_path_label(metadata, title),
                captured_at=row["captured_at"],
                excerpt=_excerpt(row["chunk_text"]),
            )
        return result


def _evidence_lines(
    item: Mapping[str, Any],
    evidence_refs: Mapping[str, EvidenceReference],
) -> list[str]:
    evidence_ids = item.get("evidence_ids") or []
    if not evidence_ids:
        if item.get("item_type") in SYSTEM_ITEM_TYPES:
            reference = item.get("metadata", {}).get("system_reference") or item.get("item_type")
            return [f"System: {reference}"]
        return ["Evidence: none"]

    lines: list[str] = []
    for evidence_id in evidence_ids:
        ref = evidence_refs.get(evidence_id)
        if ref is None:
            lines.append(f"Evidence: [{evidence_id}] unavailable")
            continue
        lines.append(f"Evidence: {_format_evidence_reference(ref)}")
    return lines


def _format_evidence_reference(ref: EvidenceReference) -> str:
    parts = [
        f"[{ref.evidence_id}]",
        _clean_inline(ref.title),
        _clean_inline(ref.path_label),
        _clean_inline(ref.captured_at),
    ]
    if ref.excerpt:
        parts.append(_clean_inline(ref.excerpt))
    return " / ".join(parts)


def _safe_path_label(metadata: Mapping[str, Any], title: str) -> str:
    relative_path = metadata.get("relative_path")
    if isinstance(relative_path, str) and relative_path.strip():
        return relative_path.strip().replace("\\", "/")
    return title


def _excerpt(text: str | None, *, max_length: int = 140) -> str | None:
    if not text:
        return None
    collapsed = _clean_inline(text)
    if len(collapsed) <= max_length:
        return collapsed
    return collapsed[: max_length - 3].rstrip() + "..."


def _clean_inline(value: str) -> str:
    return " ".join(value.split())


def _filename_for_report(report: "DailyBriefRecord") -> str:
    date_part = report.report_date or "undated"
    return f"{report.report_type}-{date_part}-{report.report_id}.md"
