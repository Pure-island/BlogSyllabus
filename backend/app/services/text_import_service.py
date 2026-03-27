from __future__ import annotations

import csv
import io
import re
from datetime import datetime

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import Article, ArticleAnalysisStatus, Source, SourceType
from app.schemas import (
    ArticleImportBatchPayload,
    ArticleImportBatchResponse,
    ArticleImportCandidate,
    ArticleImportInvalidItem,
    ArticleImportPreviewResponse,
    ArticleImportPreviewRequest,
    ManualSourceDraft,
    SourceCreate,
)
from app.services.import_service import create_analyze_batch_job
from app.services.provider_service import (
    ProviderNotConfiguredError,
    ensure_provider_settings,
    parse_article_candidates_with_provider,
)
from app.services.source_service import create_source

URL_RE = re.compile(r"https?://[^\s)>,]+", re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
RAW_SUMMARY_MAX_LENGTH = 2000
CONTENT_EXCERPT_MAX_LENGTH = 5000


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    text = value.strip()
    if not text:
        return None

    for candidate in (text, text.replace("Z", "+00:00"), f"{text}T00:00:00"):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue
    return None


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.strip().split())
    return cleaned or None


def _normalize_candidate(candidate: dict) -> ArticleImportCandidate | None:
    title = _clean_text(str(candidate.get("title") or ""))
    url_match = URL_RE.search(str(candidate.get("url") or ""))
    url = url_match.group(0).rstrip(".,;") if url_match else None
    if not title or not url:
        return None

    raw_summary = _clean_text(candidate.get("raw_summary"))
    content_excerpt = _clean_text(candidate.get("content_excerpt")) or raw_summary
    return ArticleImportCandidate(
        title=title[:300],
        url=url[:800],
        author=_clean_text(candidate.get("author")),
        published_at=_parse_datetime(candidate.get("published_at")),
        raw_summary=raw_summary[:RAW_SUMMARY_MAX_LENGTH] if raw_summary else None,
        content_excerpt=content_excerpt[:CONTENT_EXCERPT_MAX_LENGTH] if content_excerpt else None,
        source_name_snapshot=_clean_text(candidate.get("source_name_snapshot")),
    )


def _parse_csv_candidates(raw_text: str) -> tuple[list[ArticleImportCandidate], list[ArticleImportInvalidItem]]:
    candidates: list[ArticleImportCandidate] = []
    invalid: list[ArticleImportInvalidItem] = []

    sample = raw_text.strip()
    if not sample or "\n" not in sample:
        return candidates, invalid

    first_line = sample.splitlines()[0].lower()
    if "url" not in first_line or "," not in first_line:
        return candidates, invalid

    reader = csv.DictReader(io.StringIO(sample))
    for row in reader:
        normalized = _normalize_candidate(
            {
                "title": row.get("title") or row.get("name"),
                "url": row.get("url") or row.get("link"),
                "author": row.get("author"),
                "published_at": row.get("published_at") or row.get("published"),
                "raw_summary": row.get("summary") or row.get("description"),
                "content_excerpt": row.get("excerpt"),
                "source_name_snapshot": row.get("source"),
            }
        )
        if normalized:
            candidates.append(normalized)
        else:
            invalid.append(
                ArticleImportInvalidItem(raw=str(row), reason="Could not extract both title and URL.")
            )
    return candidates, invalid


def _parse_markdown_candidates(raw_text: str) -> tuple[list[ArticleImportCandidate], list[ArticleImportInvalidItem]]:
    candidates: list[ArticleImportCandidate] = []
    seen: set[tuple[str, str]] = set()
    for title, url in MARKDOWN_LINK_RE.findall(raw_text):
        key = (title.strip(), url.strip())
        if key in seen:
            continue
        seen.add(key)
        normalized = _normalize_candidate({"title": title, "url": url})
        if normalized:
            candidates.append(normalized)
    return candidates, []


def _parse_line_candidates(raw_text: str) -> tuple[list[ArticleImportCandidate], list[ArticleImportInvalidItem]]:
    candidates: list[ArticleImportCandidate] = []
    invalid: list[ArticleImportInvalidItem] = []

    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        markdown_match = MARKDOWN_LINK_RE.search(line)
        if markdown_match:
            normalized = _normalize_candidate(
                {"title": markdown_match.group(1), "url": markdown_match.group(2)}
            )
            if normalized:
                candidates.append(normalized)
            continue

        url_match = URL_RE.search(line)
        if not url_match:
            invalid.append(ArticleImportInvalidItem(raw=line, reason="No URL found."))
            continue

        url = url_match.group(0).rstrip(".,;")
        title = line[: url_match.start()].strip(" -|\t") or line[url_match.end() :].strip(" -|\t")
        if not title:
            title = url.rsplit("/", 1)[-1].replace("-", " ").replace("_", " ").strip() or url

        normalized = _normalize_candidate({"title": title, "url": url})
        if normalized:
            candidates.append(normalized)
        else:
            invalid.append(ArticleImportInvalidItem(raw=line, reason="Could not extract both title and URL."))

    return candidates, invalid


def _dedupe_candidates(candidates: list[ArticleImportCandidate]) -> list[ArticleImportCandidate]:
    deduped: list[ArticleImportCandidate] = []
    seen_urls: set[str] = set()
    for candidate in candidates:
        if candidate.url in seen_urls:
            continue
        seen_urls.add(candidate.url)
        deduped.append(candidate)
    return deduped


def _create_manual_source(session: Session, payload: ManualSourceDraft) -> Source:
    return create_source(
        session,
        SourceCreate(
            name=payload.name,
            homepage_url=payload.homepage_url,
            rss_url=None,
            source_type=SourceType.MANUAL,
            language=payload.language,
            priority=payload.priority,
            is_active=payload.is_active,
        ),
    )


def preview_article_import(
    session: Session, payload: ArticleImportPreviewRequest
) -> ArticleImportPreviewResponse:
    csv_candidates, csv_invalid = _parse_csv_candidates(payload.raw_text)
    if csv_candidates:
        candidates = csv_candidates
        invalid_items = csv_invalid
    else:
        markdown_candidates, _ = _parse_markdown_candidates(payload.raw_text)
        line_candidates, line_invalid = _parse_line_candidates(payload.raw_text)
        candidates = _dedupe_candidates(markdown_candidates + line_candidates)
        invalid_items = line_invalid

    used_llm_fallback = False
    if not candidates and payload.use_llm_fallback:
        try:
            ensure_provider_settings(session)
            candidates = parse_article_candidates_with_provider(session, payload.raw_text)
            used_llm_fallback = True
            invalid_items = []
        except ProviderNotConfiguredError:
            pass

    candidates = _dedupe_candidates(candidates)
    existing_urls = {
        url for url in session.exec(select(Article.url).where(Article.url.in_([item.url for item in candidates]))).all()
    } if candidates else set()
    duplicate_items = [item for item in candidates if item.url in existing_urls]
    parsed_items = [item for item in candidates if item.url not in existing_urls]

    return ArticleImportPreviewResponse(
        parsed_items=parsed_items,
        duplicate_items=duplicate_items,
        invalid_items=invalid_items,
        total_items=len(parsed_items) + len(duplicate_items) + len(invalid_items),
        importable_count=len(parsed_items),
        duplicate_count=len(duplicate_items),
        invalid_count=len(invalid_items),
        used_llm_fallback=used_llm_fallback,
    )


def import_article_candidates(
    session: Session, payload: ArticleImportBatchPayload
) -> ArticleImportBatchResponse:
    if not payload.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No article items to import.")
    if payload.source_id and payload.new_source:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose either an existing source or a new manual source, not both.",
        )

    source: Source | None = None
    if payload.source_id is not None:
        source = session.get(Source, payload.source_id)
        if source is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found.")
    elif payload.new_source is not None:
        source = _create_manual_source(session, payload.new_source)

    inserted_ids: list[int] = []
    duplicate_count = 0
    skipped_count = 0
    seen_urls: set[str] = set()

    for item in payload.items:
        if item.url in seen_urls:
            skipped_count += 1
            continue
        seen_urls.add(item.url)

        existing = session.exec(select(Article).where(Article.url == item.url)).first()
        if existing is not None:
            duplicate_count += 1
            continue

        article = Article(
            source_id=source.id if source else None,
            source_name_snapshot=source.name if source else item.source_name_snapshot,
            title=item.title,
            url=item.url,
            published_at=item.published_at,
            author=item.author,
            raw_summary=(item.raw_summary[:RAW_SUMMARY_MAX_LENGTH] if item.raw_summary else None),
            content_excerpt=((item.content_excerpt or item.raw_summary)[:CONTENT_EXCERPT_MAX_LENGTH] if (item.content_excerpt or item.raw_summary) else None),
            analysis_status=ArticleAnalysisStatus.PENDING,
        )
        session.add(article)
        session.flush()
        inserted_ids.append(article.id or 0)

    session.commit()

    analyze_job_id: int | None = None
    if payload.analyze_after_import and inserted_ids:
        try:
            ensure_provider_settings(session)
            analyze_job = create_analyze_batch_job(session, inserted_ids)
            analyze_job_id = analyze_job.id or 0
        except ProviderNotConfiguredError:
            analyze_job_id = None

    return ArticleImportBatchResponse(
        inserted_count=len(inserted_ids),
        duplicate_count=duplicate_count,
        skipped_count=skipped_count,
        source_id=source.id if source else None,
        analyze_job_id=analyze_job_id,
    )
