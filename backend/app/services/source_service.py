from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.models import Article, FetchStatus, Source
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


def ensure_unique_rss_url(session: Session, rss_url: str, exclude_id: Optional[int] = None) -> None:
    statement = select(Source).where(Source.rss_url == rss_url)
    existing = session.exec(statement).first()
    if existing and existing.id != exclude_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An RSS source with the same URL already exists.",
        )


def create_source(session: Session, payload: SourceCreate) -> Source:
    ensure_unique_rss_url(session, payload.rss_url)
    source = Source.model_validate(payload)
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


def update_source(session: Session, source: Source, payload: SourceUpdate) -> Source:
    updates = payload.model_dump(exclude_unset=True)
    if "rss_url" in updates:
        ensure_unique_rss_url(session, updates["rss_url"], exclude_id=source.id)

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
