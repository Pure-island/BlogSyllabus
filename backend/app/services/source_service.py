from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.models import Article, FetchStatus, Source, SourceType
from app.schemas import SourceCreate, SourceUpdate
from app.services.rss import FeedError, fetch_feed_content, normalize_entries, validate_feed


def list_sources(session: Session) -> list[tuple[Source, int]]:
    sources = session.exec(select(Source).order_by(Source.priority.asc(), Source.created_at.asc())).all()
    counts = dict(
        session.exec(
            select(Article.source_id, func.count(Article.id)).group_by(Article.source_id)
        ).all()
    )
    return [(source, counts.get(source.id, 0)) for source in sources]


def get_source_or_404(session: Session, source_id: int) -> Source:
    source = session.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found.")
    return source


def ensure_unique_rss_url(
    session: Session, rss_url: Optional[str], exclude_id: Optional[int] = None
) -> None:
    if not rss_url:
        return
    statement = select(Source).where(Source.rss_url == rss_url)
    existing = session.exec(statement).first()
    if existing and existing.id != exclude_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An RSS source with the same URL already exists.",
        )


def _resolved_source_type(requested_type: SourceType | None, rss_url: Optional[str]) -> SourceType:
    return SourceType.RSS if rss_url else requested_type or SourceType.MANUAL


def _validate_source_fields(source_type: SourceType, rss_url: Optional[str]) -> None:
    if source_type == SourceType.RSS and not rss_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="RSS sources require an RSS URL.",
        )


def create_source(session: Session, payload: SourceCreate) -> Source:
    rss_url = payload.rss_url.strip() if payload.rss_url else None
    source_type = _resolved_source_type(payload.source_type, rss_url)
    _validate_source_fields(source_type, rss_url)
    ensure_unique_rss_url(session, rss_url)
    source = Source.model_validate(
        payload.model_dump() | {"rss_url": rss_url, "source_type": source_type}
    )
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


def update_source(session: Session, source: Source, payload: SourceUpdate) -> Source:
    updates = payload.model_dump(exclude_unset=True)
    rss_url = source.rss_url
    if "rss_url" in updates:
        rss_url = updates["rss_url"].strip() if updates["rss_url"] else None
        ensure_unique_rss_url(session, rss_url, exclude_id=source.id)
        updates["rss_url"] = rss_url
    source_type = _resolved_source_type(
        updates.get("source_type", source.source_type),
        rss_url,
    )
    _validate_source_fields(source_type, rss_url)
    updates["source_type"] = source_type

    for key, value in updates.items():
        setattr(source, key, value)

    source.updated_at = datetime.now(timezone.utc)
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


def delete_source(session: Session, source: Source) -> None:
    articles = session.exec(select(Article).where(Article.source_id == source.id)).all()
    for article in articles:
        article.source_id = None
        article.updated_at = datetime.now(timezone.utc)
        if not article.source_name_snapshot:
            article.source_name_snapshot = source.name
        session.add(article)

    session.delete(source)
    session.commit()


def check_source_feed(source: Source) -> dict[str, str | int | None]:
    if source.source_type != SourceType.RSS or not source.rss_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RSS is not configured for this source.",
        )
    try:
        metadata = validate_feed(source.rss_url)
        return {
            "message": "RSS feed is valid.",
            "feed_title": metadata.get("feed_title"),
            "entry_count": metadata.get("entry_count", 0),
        }
    except FeedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - network edge case
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to validate RSS: {exc}"
        ) from exc


def fetch_articles_for_source(session: Session, source: Source) -> dict[str, int]:
    if source.source_type != SourceType.RSS or not source.rss_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RSS is not configured for this source.",
        )
    try:
        raw_feed = fetch_feed_content(source.rss_url)
        normalized_entries = normalize_entries(source, raw_feed)
        inserted_count = 0
        deduplicated_count = 0

        for entry in normalized_entries:
            existing = session.exec(select(Article).where(Article.url == entry["url"])).first()
            if existing is not None:
                deduplicated_count += 1
                continue

            article = Article(**entry)
            session.add(article)
            inserted_count += 1

        source.last_fetched_at = datetime.now(timezone.utc)
        source.last_fetch_status = FetchStatus.SUCCESS
        source.last_fetch_error = None
        source.updated_at = datetime.now(timezone.utc)
        session.add(source)
        session.commit()

        return {
            "inserted_count": inserted_count,
            "deduplicated_count": deduplicated_count,
            "total_entries": len(normalized_entries),
        }
    except FeedError as exc:
        source.last_fetched_at = datetime.now(timezone.utc)
        source.last_fetch_status = FetchStatus.FAILED
        source.last_fetch_error = str(exc)
        source.updated_at = datetime.now(timezone.utc)
        session.add(source)
        session.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - network edge case
        source.last_fetched_at = datetime.now(timezone.utc)
        source.last_fetch_status = FetchStatus.FAILED
        source.last_fetch_error = str(exc)
        source.updated_at = datetime.now(timezone.utc)
        session.add(source)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to fetch RSS feed: {exc}"
        ) from exc
