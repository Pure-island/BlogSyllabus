from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.models import (
    Article,
    ArticleAnalysisStatus,
    ArticleTag,
    DifficultyLevel,
    ReadingLog,
    ReadingStage,
    ReadingStatus,
    Source,
)
from app.schemas import (
    ArticleCreate,
    ArticleRead,
    ArticleUpdate,
    CurriculumResponse,
    ProgressBucket,
    ProgressResponse,
    ReadingLogCreate,
    ReadingLogRead,
    SourceProgressBucket,
    TodayResponse,
)
from app.services.provider_service import analyze_article_with_provider
from app.services.weekly_service import (
    build_weekly_candidates,
    get_current_weekly_review,
    get_ranked_weekly_candidate_articles,
    select_weekly_plan_articles,
)

ACTIVE_READING_STATUSES = {
    ReadingStatus.PLANNED,
    ReadingStatus.SKIMMED,
    ReadingStatus.DEEP_READ,
}

COMPLETED_READING_STATUSES = {
    ReadingStatus.REVIEWED,
    ReadingStatus.MASTERED,
}

CORE_SCORE_THRESHOLD = 0.75
RAW_SUMMARY_MAX_LENGTH = 2000
CONTENT_EXCERPT_MAX_LENGTH = 5000


def _clamp_text(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    return value[:max_length]


def normalize_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        clean = tag.strip().lower()
        if not clean or clean in seen:
            continue
        normalized.append(clean)
        seen.add(clean)
    return normalized


def _article_statement():
    return select(Article).options(selectinload(Article.tags), selectinload(Article.source))


def _sync_article_tags(session: Session, article: Article, tags: list[str]) -> None:
    normalized_tags = normalize_tags(tags)
    existing_tags = session.exec(select(ArticleTag).where(ArticleTag.article_id == article.id)).all()
    existing_map = {item.tag: item for item in existing_tags}

    for tag in normalized_tags:
        if tag in existing_map:
            continue
        session.add(ArticleTag(article_id=article.id, tag=tag))

    for tag, existing in existing_map.items():
        if tag not in normalized_tags:
            session.delete(existing)


def article_to_read(article: Article) -> ArticleRead:
    return ArticleRead(
        id=article.id or 0,
        source_id=article.source_id,
        source_name_snapshot=article.source_name_snapshot,
        title=article.title,
        url=article.url,
        published_at=article.published_at,
        author=article.author,
        raw_summary=_clamp_text(article.raw_summary, RAW_SUMMARY_MAX_LENGTH),
        content_excerpt=_clamp_text(article.content_excerpt, CONTENT_EXCERPT_MAX_LENGTH),
        difficulty=article.difficulty,
        stage=article.stage,
        estimated_minutes=article.estimated_minutes,
        status=article.status,
        is_core=article.is_core,
        core_score=article.core_score,
        core_reason=article.core_reason,
        checkpoint_questions=article.checkpoint_questions,
        tags=[tag.tag for tag in article.tags],
        analysis_status=article.analysis_status,
        analysis_error=article.analysis_error,
        last_analyzed_at=article.last_analyzed_at,
        created_at=article.created_at,
        updated_at=article.updated_at,
    )


def get_article_or_404(session: Session, article_id: int) -> Article:
    article = session.exec(_article_statement().where(Article.id == article_id)).first()
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found.")
    return article


def list_articles(
    session: Session,
    *,
    stage: ReadingStage | None = None,
    status_value: ReadingStatus | None = None,
    difficulty: DifficultyLevel | None = None,
    source_id: int | None = None,
    is_core: bool | None = None,
    tag: str | None = None,
    inbox_only: bool = False,
) -> list[Article]:
    statement = _article_statement()

    if inbox_only:
        statement = statement.where(Article.stage.is_(None))
    if stage is not None:
        statement = statement.where(Article.stage == stage)
    if status_value is not None:
        statement = statement.where(Article.status == status_value)
    if difficulty is not None:
        statement = statement.where(Article.difficulty == difficulty)
    if source_id is not None:
        statement = statement.where(Article.source_id == source_id)
    if is_core is not None:
        statement = statement.where(Article.is_core == is_core)
    if tag:
        tag_lower = tag.strip().lower()
        statement = statement.join(ArticleTag).where(ArticleTag.tag == tag_lower)

    return session.exec(statement.order_by(Article.created_at.desc())).all()


def create_article(session: Session, payload: ArticleCreate) -> Article:
    existing = session.exec(select(Article).where(Article.url == payload.url)).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An article with this URL already exists.",
        )

    if payload.source_id is not None and session.get(Source, payload.source_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found.")

    article = Article(
        source_id=payload.source_id,
        source_name_snapshot=payload.source_name_snapshot,
        title=payload.title,
        url=payload.url,
        published_at=payload.published_at,
        author=payload.author,
        raw_summary=payload.raw_summary,
        content_excerpt=payload.content_excerpt,
        difficulty=payload.difficulty,
        stage=payload.stage,
        estimated_minutes=payload.estimated_minutes,
        status=payload.status,
        is_core=payload.is_core,
        core_score=payload.core_score,
        core_reason=payload.core_reason,
        checkpoint_questions=payload.checkpoint_questions,
        analysis_status=ArticleAnalysisStatus.PENDING,
    )
    session.add(article)
    session.commit()
    session.refresh(article)
    _sync_article_tags(session, article, payload.tags)
    session.commit()
    return get_article_or_404(session, article.id or 0)


def update_article(session: Session, article: Article, payload: ArticleUpdate) -> Article:
    updates = payload.model_dump(exclude_unset=True)
    tags = updates.pop("tags", None)

    for key, value in updates.items():
        setattr(article, key, value)

    article.updated_at = datetime.now(timezone.utc)
    session.add(article)
    session.commit()
    session.refresh(article)

    if tags is not None:
        _sync_article_tags(session, article, tags)
        session.commit()

    return get_article_or_404(session, article.id or 0)


def analyze_article(session: Session, article: Article) -> Article:
    source = session.get(Source, article.source_id) if article.source_id else None
    analysis = analyze_article_with_provider(session, article, source)

    article.difficulty = analysis["difficulty"]
    article.stage = analysis["stage"]
    article.estimated_minutes = analysis["estimated_minutes"]
    article.raw_summary = analysis["one_sentence_summary"]
    article.checkpoint_questions = analysis["checkpoint_questions"]
    article.core_score = max(0, min(1, analysis["core_score"]))
    article.core_reason = analysis["core_reason"]
    article.is_core = article.core_score >= CORE_SCORE_THRESHOLD
    article.analysis_status = ArticleAnalysisStatus.COMPLETE
    article.analysis_error = None
    article.last_analyzed_at = datetime.now(timezone.utc)
    article.updated_at = datetime.now(timezone.utc)

    session.add(article)
    session.commit()
    session.refresh(article)
    _sync_article_tags(session, article, analysis["tags"])
    session.commit()

    return get_article_or_404(session, article.id or 0)


def mark_article_analysis_failed(session: Session, article: Article, error_message: str) -> None:
    article.analysis_status = ArticleAnalysisStatus.FAILED
    article.analysis_error = error_message
    article.last_analyzed_at = datetime.now(timezone.utc)
    article.updated_at = datetime.now(timezone.utc)
    session.add(article)
    session.commit()


def get_curriculum(session: Session) -> CurriculumResponse:
    articles = list_articles(session)
    buckets = {
        "foundation": [],
        "core": [],
        "frontier": [],
        "update": [],
        "unassigned": [],
    }

    for article in articles:
        if article.stage is None:
            buckets["unassigned"].append(article_to_read(article))
        else:
            buckets[article.stage.value].append(article_to_read(article))

    return CurriculumResponse(**buckets)


def generate_today(session: Session) -> TodayResponse:
    articles = session.exec(
        _article_statement()
        .where(Article.stage.is_not(None))
        .where(Article.status.in_(list(ACTIVE_READING_STATUSES)))
    ).all()

    weekly_review = get_current_weekly_review(session)
    if weekly_review is not None:
        article_by_id = {article.id or 0: article for article in articles}
        primary_article = next(
            (
                article_by_id[article_id]
                for article_id in weekly_review.primary_article_ids
                if article_id in article_by_id
            ),
            None,
        )
        secondary_article = next(
            (
                article_by_id[article_id]
                for article_id in weekly_review.supplemental_article_ids
                if article_id in article_by_id and article_id != (primary_article.id or 0 if primary_article else None)
            ),
            None,
        )
        if primary_article and secondary_article is None:
            secondary_article = next(
                (
                    article_by_id[article_id]
                    for article_id in weekly_review.primary_article_ids
                    if article_id in article_by_id and article_id != (primary_article.id or 0)
                ),
                None,
            )

        candidate_count = len(
            {
                *[article_id for article_id in weekly_review.primary_article_ids if article_id in article_by_id],
                *[article_id for article_id in weekly_review.supplemental_article_ids if article_id in article_by_id],
            }
        )

        if primary_article or secondary_article:
            return TodayResponse(
                generated_at=datetime.now(timezone.utc),
                primary_article=article_to_read(primary_article) if primary_article else None,
                secondary_article=article_to_read(secondary_article) if secondary_article else None,
                candidate_count=candidate_count,
            )

    filtered_articles = [candidate.article for candidate in build_weekly_candidates(articles)]
    ranked_articles = get_ranked_weekly_candidate_articles(filtered_articles)
    primary_articles, supplemental_articles = select_weekly_plan_articles(filtered_articles)
    primary_article = primary_articles[0] if primary_articles else (ranked_articles[0] if ranked_articles else None)
    secondary_article = supplemental_articles[0] if supplemental_articles else None
    if primary_article and secondary_article and secondary_article.id == primary_article.id:
        secondary_article = next(
            (article for article in supplemental_articles if article.id != primary_article.id),
            None,
        )
    if primary_article and secondary_article is None:
        secondary_article = next(
            (article for article in ranked_articles if article.id != primary_article.id),
            None,
        )

    return TodayResponse(
        generated_at=datetime.now(timezone.utc),
        primary_article=article_to_read(primary_article) if primary_article else None,
        secondary_article=article_to_read(secondary_article) if secondary_article else None,
        candidate_count=len(ranked_articles),
    )


def get_progress(session: Session) -> ProgressResponse:
    articles = list_articles(session)
    total_articles = len(articles)
    completed_articles = len([item for item in articles if item.status in COMPLETED_READING_STATUSES])
    in_progress_articles = len([item for item in articles if item.status in ACTIVE_READING_STATUSES])

    stage_breakdown = Counter((article.stage.value if article.stage else "unassigned") for article in articles)
    status_breakdown = Counter(article.status.value for article in articles)
    tag_breakdown = Counter(tag.tag for article in articles for tag in article.tags)

    source_breakdown: list[SourceProgressBucket] = []
    source_groups: dict[tuple[int | None, str], list[Article]] = {}
    for article in articles:
        source_name = article.source.name if article.source else article.source_name_snapshot or "Unlinked source"
        key = (article.source_id, source_name)
        source_groups.setdefault(key, []).append(article)

    for (source_id, source_name), source_articles in source_groups.items():
        source_breakdown.append(
            SourceProgressBucket(
                source_id=source_id,
                source_name=source_name,
                total=len(source_articles),
                completed=len(
                    [article for article in source_articles if article.status in COMPLETED_READING_STATUSES]
                ),
                in_progress=len(
                    [article for article in source_articles if article.status in ACTIVE_READING_STATUSES]
                ),
            )
        )

    return ProgressResponse(
        total_articles=total_articles,
        completed_articles=completed_articles,
        in_progress_articles=in_progress_articles,
        stage_breakdown=[
            ProgressBucket(label=label, count=count)
            for label, count in sorted(stage_breakdown.items(), key=lambda item: item[0])
        ],
        status_breakdown=[
            ProgressBucket(label=label, count=count)
            for label, count in sorted(status_breakdown.items(), key=lambda item: item[0])
        ],
        tag_breakdown=[
            ProgressBucket(label=label, count=count)
            for label, count in tag_breakdown.most_common(15)
        ],
        source_breakdown=sorted(source_breakdown, key=lambda item: item.source_name.lower()),
    )


def list_reading_logs(session: Session) -> list[ReadingLogRead]:
    logs = session.exec(select(ReadingLog).order_by(ReadingLog.read_date.desc(), ReadingLog.id.desc())).all()
    article_lookup = {
        article_id: {"title": article_title, "url": article_url}
        for article_id, article_title, article_url in session.exec(
            select(Article.id, Article.title, Article.url)
        ).all()
    }
    return [
        ReadingLogRead(
            id=log.id or 0,
            article_id=log.article_id,
            article_title=article_lookup.get(log.article_id, {}).get("title", "Unknown article"),
            article_url=article_lookup.get(log.article_id, {}).get("url"),
            read_date=log.read_date,
            status_after_read=log.status_after_read,
            one_sentence_summary=log.one_sentence_summary,
            key_insight=log.key_insight,
            open_question=log.open_question,
            next_action=log.next_action,
            created_at=log.created_at,
        )
        for log in logs
    ]


def create_reading_log(session: Session, payload: ReadingLogCreate) -> ReadingLogRead:
    article = session.get(Article, payload.article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found.")

    log = ReadingLog(**payload.model_dump())
    session.add(log)
    session.commit()
    session.refresh(log)

    return ReadingLogRead(
        id=log.id or 0,
        article_id=log.article_id,
        article_title=article.title,
        article_url=article.url,
        read_date=log.read_date,
        status_after_read=log.status_after_read,
        one_sentence_summary=log.one_sentence_summary,
        key_insight=log.key_insight,
        open_question=log.open_question,
        next_action=log.next_action,
        created_at=log.created_at,
    )
