"""Local full-text search over evidence chunks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
import sqlite3
from typing import Any, Sequence

from ego_data_core.kernel.time import local_date_bounds_as_utc
from ego_data_core.storage.db import get_connection, run_migrations


DEFAULT_SEARCH_LIMIT = 20
MAX_SEARCH_LIMIT = 100


@dataclass(frozen=True)
class SearchResult:
    evidence_id: str
    chunk_id: str
    title: str | None
    snippet: str
    captured_at: str
    source_id: str
    chunk_index: int
    score: float | None
    match_type: str


class LocalSearchService:
    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        prefer_fts: bool = True,
    ) -> None:
        self.database_path = database_path
        self.prefer_fts = prefer_fts

    def search(
        self,
        query: str,
        *,
        source_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = DEFAULT_SEARCH_LIMIT,
    ) -> dict[str, Any]:
        normalized_query = _normalize_query(query)
        safe_limit = min(max(int(limit), 1), MAX_SEARCH_LIMIT)
        start, end = _date_filters(date_from, date_to)
        run_migrations(self.database_path)

        if self.prefer_fts:
            try:
                items = self._search_fts(
                    normalized_query,
                    source_id=source_id,
                    start=start,
                    end=end,
                    limit=safe_limit,
                )
                return _search_payload(
                    query=normalized_query,
                    items=items,
                    limit=safe_limit,
                    source_id=source_id,
                    date_from=date_from,
                    date_to=date_to,
                    backend="fts5",
                )
            except sqlite3.OperationalError:
                pass

        items = self._search_like(
            normalized_query,
            source_id=source_id,
            start=start,
            end=end,
            limit=safe_limit,
        )
        return _search_payload(
            query=normalized_query,
            items=items,
            limit=safe_limit,
            source_id=source_id,
            date_from=date_from,
            date_to=date_to,
            backend="like",
        )

    def _search_fts(
        self,
        query: str,
        *,
        source_id: str | None,
        start: str | None,
        end: str | None,
        limit: int,
    ) -> list[SearchResult]:
        match_query = _fts_query(query)
        with get_connection(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT
                  fts.evidence_id,
                  fts.chunk_id,
                  raw.title,
                  snippet(evidence_text_fts, 2, '[', ']', '...', 24) AS snippet,
                  ev.captured_at,
                  raw.source_id,
                  chunks.chunk_index,
                  bm25(evidence_text_fts) AS score
                FROM evidence_text_fts AS fts
                JOIN evidence_text_chunks AS chunks
                  ON chunks.chunk_id = fts.chunk_id
                JOIN evidence AS ev
                  ON ev.evidence_id = fts.evidence_id
                JOIN raw_objects AS raw
                  ON raw.raw_object_id = ev.raw_object_id
                WHERE evidence_text_fts MATCH ?
                  AND (? IS NULL OR raw.source_id = ?)
                  AND (? IS NULL OR ev.captured_at >= ?)
                  AND (? IS NULL OR ev.captured_at < ?)
                ORDER BY score ASC, ev.captured_at DESC, fts.chunk_id ASC
                LIMIT ?
                """,
                (
                    match_query,
                    source_id,
                    source_id,
                    start,
                    start,
                    end,
                    end,
                    limit,
                ),
            ).fetchall()
        return [_row_to_result(row, match_type="fts5") for row in rows]

    def _search_like(
        self,
        query: str,
        *,
        source_id: str | None,
        start: str | None,
        end: str | None,
        limit: int,
    ) -> list[SearchResult]:
        terms = _query_terms(query)
        where_clauses = [
            "(LOWER(chunks.text) LIKE ? OR LOWER(raw.title) LIKE ?)",
        ]
        params: list[Any] = []
        first_term = f"%{terms[0].lower()}%"
        params.extend([first_term, first_term])
        for term in terms[1:]:
            pattern = f"%{term.lower()}%"
            where_clauses.append("(LOWER(chunks.text) LIKE ? OR LOWER(raw.title) LIKE ?)")
            params.extend([pattern, pattern])
        if source_id:
            where_clauses.append("raw.source_id = ?")
            params.append(source_id)
        if start:
            where_clauses.append("ev.captured_at >= ?")
            params.append(start)
        if end:
            where_clauses.append("ev.captured_at < ?")
            params.append(end)
        params.append(limit)

        with get_connection(self.database_path) as connection:
            rows = connection.execute(
                f"""
                SELECT
                  ev.evidence_id,
                  chunks.chunk_id,
                  raw.title,
                  chunks.text AS text,
                  ev.captured_at,
                  raw.source_id,
                  chunks.chunk_index
                FROM evidence_text_chunks AS chunks
                JOIN evidence AS ev
                  ON ev.evidence_id = chunks.evidence_id
                JOIN raw_objects AS raw
                  ON raw.raw_object_id = ev.raw_object_id
                WHERE {' AND '.join(where_clauses)}
                ORDER BY ev.captured_at DESC, chunks.chunk_id ASC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [
            SearchResult(
                evidence_id=row["evidence_id"],
                chunk_id=row["chunk_id"],
                title=row["title"],
                snippet=_snippet(row["text"], terms),
                captured_at=row["captured_at"],
                source_id=row["source_id"],
                chunk_index=row["chunk_index"],
                score=float(_like_score(row["text"], terms)),
                match_type="like",
            )
            for row in rows
        ]


def search_to_dict(result: SearchResult) -> dict[str, Any]:
    return {
        "evidence_id": result.evidence_id,
        "chunk_id": result.chunk_id,
        "title": result.title,
        "snippet": result.snippet,
        "captured_at": result.captured_at,
        "source_id": result.source_id,
        "chunk_index": result.chunk_index,
        "score": result.score,
        "match_type": result.match_type,
    }


def _search_payload(
    *,
    query: str,
    items: Sequence[SearchResult],
    limit: int,
    source_id: str | None,
    date_from: str | None,
    date_to: str | None,
    backend: str,
) -> dict[str, Any]:
    return {
        "query": query,
        "backend": backend,
        "items": [search_to_dict(item) for item in items],
        "total": len(items),
        "limit": limit,
        "filters": {
            "source_id": source_id,
            "date_from": date_from,
            "date_to": date_to,
        },
    }


def _row_to_result(row, *, match_type: str) -> SearchResult:
    return SearchResult(
        evidence_id=row["evidence_id"],
        chunk_id=row["chunk_id"],
        title=row["title"],
        snippet=row["snippet"],
        captured_at=row["captured_at"],
        source_id=row["source_id"],
        chunk_index=row["chunk_index"],
        score=float(row["score"]) if row["score"] is not None else None,
        match_type=match_type,
    )


def _normalize_query(query: str) -> str:
    normalized = " ".join(query.split())
    if not normalized:
        raise ValueError("Search query must not be empty")
    return normalized


def _query_terms(query: str) -> list[str]:
    terms = re.findall(r"[\w\u4e00-\u9fff]+", query, flags=re.UNICODE)
    if not terms:
        raise ValueError("Search query must include at least one word")
    return terms


def _fts_query(query: str) -> str:
    terms = _query_terms(query)
    quoted_terms = []
    for term in terms:
        escaped = term.replace('"', '""')
        quoted_terms.append(f'"{escaped}"')
    return " AND ".join(quoted_terms)


def _date_filters(date_from: str | None, date_to: str | None) -> tuple[str | None, str | None]:
    start = (
        local_date_bounds_as_utc(date.fromisoformat(date_from).isoformat())[0]
        if date_from
        else None
    )
    end = (
        local_date_bounds_as_utc(date.fromisoformat(date_to).isoformat())[1]
        if date_to
        else None
    )
    return start, end


def _snippet(text: str, terms: Sequence[str], *, width: int = 160) -> str:
    lowered = text.lower()
    first_index = min(
        (index for term in terms if (index := lowered.find(term.lower())) >= 0),
        default=0,
    )
    start = max(0, first_index - width // 3)
    end = min(len(text), start + width)
    snippet = " ".join(text[start:end].split())
    if start > 0:
        snippet = f"...{snippet}"
    if end < len(text):
        snippet = f"{snippet}..."
    for term in terms:
        snippet = re.sub(
            re.escape(term),
            lambda match: f"[{match.group(0)}]",
            snippet,
            flags=re.IGNORECASE,
        )
    return snippet


def _like_score(text: str, terms: Sequence[str]) -> int:
    lowered = text.lower()
    return sum(lowered.count(term.lower()) for term in terms)
