from __future__ import annotations

import threading
import time
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core.config import get_settings
from app.db import engine
from app.models import (
    Article,
    ArticleAnalysisStatus,
    FetchStatus,
    ImportJob,
    ImportJobItem,
    ItemAnalysisStatus,
    JobPhase,
    JobStatus,
    JobType,
    Source,
    SourceType,
)
from app.schemas import ImportJobItemRead, ImportJobRead
from app.services.article_service import analyze_article, get_article_or_404, mark_article_analysis_failed
from app.services.provider_service import ProviderNotConfiguredError, ensure_provider_settings
from app.services.rss import (
    FeedError,
    fetch_feed_content,
    normalize_entries,
)

settings = get_settings()
_processor_lock = threading.Lock()
_processor_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def import_job_to_read(session: Session, job: ImportJob) -> ImportJobRead:
    items = session.exec(select(ImportJobItem).where(ImportJobItem.job_id == job.id)).all()
    sources = {
        source.id: source.name
        for source in session.exec(select(Source)).all()
    }
    return ImportJobRead(
        id=job.id or 0,
        job_type=job.job_type,
        status=job.status,
        phase=job.phase,
        total_sources=job.total_sources,
        processed_sources=job.processed_sources,
        successful_sources=job.successful_sources,
        failed_sources=job.failed_sources,
        inserted_articles=job.inserted_articles,
        deduplicated_articles=job.deduplicated_articles,
        pending_analysis_articles=job.pending_analysis_articles,
        analyzed_articles=job.analyzed_articles,
        failed_analysis_articles=job.failed_analysis_articles,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        items=[
            ImportJobItemRead(
                id=item.id or 0,
                source_id=item.source_id,
                source_name=sources.get(item.source_id) if item.source_id else None,
                status=item.status,
                phase=item.phase,
                total_entries=item.total_entries,
                inserted_entries=item.inserted_entries,
                deduplicated_entries=item.deduplicated_entries,
                analysis_status=item.analysis_status,
                error_message=item.error_message,
                started_at=item.started_at,
                finished_at=item.finished_at,
            )
            for item in items
        ],
    )


def list_import_jobs(session: Session) -> list[ImportJobRead]:
    jobs = session.exec(select(ImportJob).order_by(ImportJob.created_at.desc())).all()
    return [import_job_to_read(session, job) for job in jobs]


def get_import_job_or_404(session: Session, job_id: int) -> ImportJob:
    job = session.get(ImportJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found.")
    return job


def get_import_job_read(session: Session, job_id: int) -> ImportJobRead:
    return import_job_to_read(session, get_import_job_or_404(session, job_id))


def create_fetch_active_job(session: Session) -> ImportJob:
    sources = session.exec(
        select(Source)
        .where(Source.is_active.is_(True))
        .where(Source.source_type == SourceType.RSS)
        .where(Source.rss_url.is_not(None))
    ).all()
    job = ImportJob(
        job_type=JobType.FETCH_ACTIVE_SOURCES,
        status=JobStatus.QUEUED,
        phase=JobPhase.QUEUED,
        total_sources=len(sources),
        payload={"source_ids": [source.id for source in sources]},
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    for source in sources:
        session.add(ImportJobItem(job_id=job.id or 0, source_id=source.id))
    session.commit()
    return job


def create_fetch_single_source_job(session: Session, source_id: int) -> ImportJob:
    source = session.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found.")
    if source.source_type != SourceType.RSS or not source.rss_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RSS is not configured for this source.",
        )

    job = ImportJob(
        job_type=JobType.FETCH_SOURCE,
        status=JobStatus.QUEUED,
        phase=JobPhase.QUEUED,
        total_sources=1,
        payload={"source_ids": [source.id]},
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    session.add(ImportJobItem(job_id=job.id or 0, source_id=source.id))
    session.commit()
    return job


def create_analyze_batch_job(session: Session, article_ids: list[int] | None = None) -> ImportJob:
    if article_ids is None:
        article_ids = list(
            session.exec(
                select(Article.id).where(Article.analysis_status != ArticleAnalysisStatus.COMPLETE)
            ).all()
        )

    job = ImportJob(
        job_type=JobType.ANALYZE_BATCH,
        status=JobStatus.QUEUED,
        phase=JobPhase.QUEUED,
        payload={"article_ids": article_ids},
        pending_analysis_articles=len(article_ids),
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def retry_import_job(session: Session, job_id: int) -> ImportJob:
    job = get_import_job_or_404(session, job_id)
    job.status = JobStatus.QUEUED
    job.phase = JobPhase.QUEUED
    job.error_message = None
    job.started_at = None
    job.finished_at = None
    job.processed_sources = 0
    job.successful_sources = 0
    job.failed_sources = 0
    job.inserted_articles = 0
    job.deduplicated_articles = 0
    job.pending_analysis_articles = 0
    job.analyzed_articles = 0
    job.failed_analysis_articles = 0
    session.add(job)

    items = session.exec(select(ImportJobItem).where(ImportJobItem.job_id == job.id)).all()
    for item in items:
        item.status = JobStatus.QUEUED
        item.phase = JobPhase.QUEUED
        item.total_entries = 0
        item.inserted_entries = 0
        item.deduplicated_entries = 0
        item.analysis_status = ItemAnalysisStatus.PENDING
        item.error_message = None
        item.started_at = None
        item.finished_at = None
        session.add(item)

    session.commit()
    return job


def _fetch_articles_for_source(
    session: Session, source: Source, phase_callback=None
) -> tuple[dict[str, int | str | list[str]], list[int]]:
    if not source.rss_url:
        raise FeedError("RSS is not configured for this source.")
    if phase_callback:
        phase_callback(JobPhase.FETCHING)
    normalized_entries = normalize_entries(source, fetch_feed_content(source.rss_url))
    if phase_callback:
        phase_callback(JobPhase.DEDUPING)
    urls = [entry["url"] for entry in normalized_entries]
    existing_urls = set()
    if urls:
        existing_urls = set(session.exec(select(Article.url).where(Article.url.in_(urls))).all())

    inserted_ids: list[int] = []
    inserted_count = 0
    deduplicated_count = 0
    if phase_callback:
        phase_callback(JobPhase.INSERTING)

    for entry in normalized_entries:
        if entry["url"] in existing_urls:
            deduplicated_count += 1
            continue

        article = Article(
            source_id=entry["source_id"],
            source_name_snapshot=entry["source_name_snapshot"],
            title=entry["title"],
            url=entry["url"],
            published_at=entry["published_at"],
            author=entry["author"],
            raw_summary=entry["raw_summary"],
            content_excerpt=entry["content_excerpt"],
            analysis_status=ArticleAnalysisStatus.PENDING,
        )
        session.add(article)
        session.flush()
        inserted_ids.append(article.id or 0)
        inserted_count += 1

    source.last_fetched_at = _utc_now()
    source.last_fetch_status = FetchStatus.SUCCESS
    source.last_fetch_error = None
    source.updated_at = _utc_now()
    session.add(source)
    session.commit()

    return (
        {
            "inserted_count": inserted_count,
            "deduplicated_count": deduplicated_count,
            "total_entries": len(normalized_entries),
        },
        inserted_ids,
    )


def fetch_source_sync(session: Session, source: Source) -> dict[str, int]:
    try:
        result, _ = _fetch_articles_for_source(session, source)
        return result
    except FeedError as exc:
        source.last_fetched_at = _utc_now()
        source.last_fetch_status = FetchStatus.FAILED
        source.last_fetch_error = str(exc)
        source.updated_at = _utc_now()
        session.add(source)
        session.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - network edge case
        source.last_fetched_at = _utc_now()
        source.last_fetch_status = FetchStatus.FAILED
        source.last_fetch_error = str(exc)
        source.updated_at = _utc_now()
        session.add(source)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch RSS feed: {exc}",
        ) from exc


def _mark_item_failed(session: Session, item: ImportJobItem, message: str) -> None:
    item.status = JobStatus.FAILED
    item.phase = JobPhase.COMPLETED
    item.error_message = message
    item.finished_at = _utc_now()
    session.add(item)


def _process_fetch_job(job_id: int) -> None:
    with Session(engine) as session:
        job = get_import_job_or_404(session, job_id)
        source_ids = job.payload.get("source_ids", [])
        sources = [
            source
            for source in session.exec(select(Source).where(Source.id.in_(source_ids))).all()
            if source.id is not None
        ]
        items = {
            item.source_id: item
            for item in session.exec(select(ImportJobItem).where(ImportJobItem.job_id == job.id)).all()
        }
        job.status = JobStatus.RUNNING
        job.phase = JobPhase.FETCHING
        job.started_at = _utc_now()
        job.total_sources = len(sources)
        session.add(job)
        session.commit()

        inserted_article_ids_by_source: dict[int, list[int]] = defaultdict(list)

        for source in sources:
            item = items.get(source.id)
            if item is None:
                continue

            def phase_callback(phase: JobPhase) -> None:
                item.phase = phase
                job.phase = phase
                session.add(item)
                session.add(job)
                session.commit()

            item.status = JobStatus.RUNNING
            item.phase = JobPhase.FETCHING
            item.started_at = _utc_now()
            session.add(item)
            session.commit()

            try:
                result, inserted_ids = _fetch_articles_for_source(
                    session, source, phase_callback=phase_callback
                )
                inserted_article_ids_by_source[source.id or 0].extend(inserted_ids)

                item.total_entries = result["total_entries"]
                item.inserted_entries = result["inserted_count"]
                item.deduplicated_entries = result["deduplicated_count"]
                item.status = JobStatus.SUCCESS
                item.phase = JobPhase.COMPLETED
                item.finished_at = _utc_now()
                item.analysis_status = (
                    ItemAnalysisStatus.PENDING if inserted_ids else ItemAnalysisStatus.SKIPPED
                )
                item.error_message = None
                session.add(item)

                job.processed_sources += 1
                job.successful_sources += 1
                job.inserted_articles += result["inserted_count"]
                job.deduplicated_articles += result["deduplicated_count"]
                session.add(job)
                session.commit()
            except Exception as exc:  # pragma: no cover - exercised in service tests later
                _mark_item_failed(session, item, str(exc))
                job.processed_sources += 1
                job.failed_sources += 1
                job.status = JobStatus.PARTIAL_SUCCESS
                job.error_message = str(exc)
                session.add(job)
                session.commit()

        all_inserted_ids = [article_id for ids in inserted_article_ids_by_source.values() for article_id in ids]
        job.pending_analysis_articles = len(all_inserted_ids)
        session.add(job)
        session.commit()

        if not all_inserted_ids:
            job.phase = JobPhase.COMPLETED
            job.status = JobStatus.SUCCESS if job.failed_sources == 0 else JobStatus.PARTIAL_SUCCESS
            job.finished_at = _utc_now()
            session.add(job)
            session.commit()
            return

        try:
            ensure_provider_settings(session)
        except ProviderNotConfiguredError as exc:
            for source_id, article_ids in inserted_article_ids_by_source.items():
                item = items.get(source_id)
                if item is None or not article_ids:
                    continue
                item.analysis_status = ItemAnalysisStatus.BLOCKED
                item.error_message = exc.detail
                session.add(item)
            for article_id in all_inserted_ids:
                article = get_article_or_404(session, article_id)
                article.analysis_status = ArticleAnalysisStatus.BLOCKED
                article.analysis_error = exc.detail
                article.updated_at = _utc_now()
                session.add(article)
            job.status = JobStatus.PARTIAL_SUCCESS
            job.phase = JobPhase.ANALYSIS_PENDING
            job.error_message = exc.detail
            job.finished_at = _utc_now()
            session.add(job)
            session.commit()
            return

        job.phase = JobPhase.ANALYZING
        session.add(job)
        session.commit()

        for source_id, article_ids in inserted_article_ids_by_source.items():
            item = items.get(source_id)
            source_failures = 0
            source_successes = 0
            for article_id in article_ids:
                article = get_article_or_404(session, article_id)
                try:
                    analyze_article(session, article)
                    source_successes += 1
                    job.analyzed_articles += 1
                except Exception as exc:  # pragma: no cover - provider/network dependent
                    mark_article_analysis_failed(session, article, str(exc))
                    source_failures += 1
                    job.failed_analysis_articles += 1
                finally:
                    job.pending_analysis_articles = max(job.pending_analysis_articles - 1, 0)
                    session.add(job)
                    session.commit()

            if item is not None:
                if source_failures and source_successes:
                    item.analysis_status = ItemAnalysisStatus.FAILED
                    item.error_message = "Some article analyses failed."
                elif source_failures:
                    item.analysis_status = ItemAnalysisStatus.FAILED
                    item.error_message = "Article analysis failed."
                elif article_ids:
                    item.analysis_status = ItemAnalysisStatus.COMPLETE
                    item.error_message = None
                session.add(item)
                session.commit()

        job.phase = JobPhase.COMPLETED
        job.finished_at = _utc_now()
        if job.failed_sources == 0 and job.failed_analysis_articles == 0:
            job.status = JobStatus.SUCCESS
            job.error_message = None
        else:
            job.status = JobStatus.PARTIAL_SUCCESS
        session.add(job)
        session.commit()


def _process_analyze_batch_job(job_id: int) -> None:
    with Session(engine) as session:
        job = get_import_job_or_404(session, job_id)
        job.status = JobStatus.RUNNING
        job.phase = JobPhase.ANALYZING
        job.started_at = _utc_now()
        session.add(job)
        session.commit()

        try:
            ensure_provider_settings(session)
        except ProviderNotConfiguredError as exc:
            job.status = JobStatus.BLOCKED
            job.phase = JobPhase.ANALYSIS_PENDING
            job.error_message = exc.detail
            job.finished_at = _utc_now()
            session.add(job)
            session.commit()
            return

        article_ids = job.payload.get("article_ids", [])
        if not article_ids:
            article_ids = list(
                session.exec(
                    select(Article.id).where(Article.analysis_status != ArticleAnalysisStatus.COMPLETE)
                ).all()
            )

        job.pending_analysis_articles = len(article_ids)
        session.add(job)
        session.commit()

        for article_id in article_ids:
            article = get_article_or_404(session, article_id)
            try:
                analyze_article(session, article)
                job.analyzed_articles += 1
            except Exception as exc:  # pragma: no cover - provider/network dependent
                mark_article_analysis_failed(session, article, str(exc))
                job.failed_analysis_articles += 1
            finally:
                job.pending_analysis_articles = max(job.pending_analysis_articles - 1, 0)
                session.add(job)
                session.commit()

        job.phase = JobPhase.COMPLETED
        job.finished_at = _utc_now()
        job.status = JobStatus.SUCCESS if job.failed_analysis_articles == 0 else JobStatus.PARTIAL_SUCCESS
        session.add(job)
        session.commit()


def process_next_job() -> bool:
    with Session(engine) as session:
        job = session.exec(
            select(ImportJob).where(ImportJob.status == JobStatus.QUEUED).order_by(ImportJob.created_at.asc())
        ).first()
        if job is None:
            return False
        job_id = job.id or 0

    if job.job_type in {JobType.FETCH_ACTIVE_SOURCES, JobType.FETCH_SOURCE}:
        _process_fetch_job(job_id)
    elif job.job_type == JobType.ANALYZE_BATCH:
        _process_analyze_batch_job(job_id)
    return True


def _processor_loop() -> None:
    while not _stop_event.is_set():
        try:
            found_job = process_next_job()
        except Exception:
            found_job = False
        time.sleep(0.5 if found_job else 2)


def start_background_processor() -> None:
    global _processor_thread
    if settings.app_env == "test":
        return

    with _processor_lock:
        if _processor_thread and _processor_thread.is_alive():
            return
        _stop_event.clear()
        _processor_thread = threading.Thread(target=_processor_loop, daemon=True, name="import-processor")
        _processor_thread.start()


def stop_background_processor() -> None:
    _stop_event.set()
