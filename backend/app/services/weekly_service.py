from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.models import Article, ArticleTag, ReadingStage, ReadingStatus, WeeklyReview
from app.schemas import (
    ArticleRead,
    WeeklyPlannedArticleMetadata,
    WeeklyPlannedArticleRead,
    WeeklyReviewRead,
)
from app.services.provider_service import (
    ProviderNotConfiguredError,
    plan_weekly_curriculum_with_provider,
)
from app.services.settings_service import get_settings_payload

ACTIVE_STATUSES = {
    ReadingStatus.PLANNED,
    ReadingStatus.SKIMMED,
    ReadingStatus.DEEP_READ,
}

SEQUENCE_STAGE_ORDER = {
    ReadingStage.FOUNDATION: 0,
    ReadingStage.CORE: 1,
    ReadingStage.FRONTIER: 2,
    ReadingStage.UPDATE: 3,
}

TOPIC_SELECTION_STAGE_WEIGHT = {
    ReadingStage.CORE: 0,
    ReadingStage.FOUNDATION: 1,
    ReadingStage.FRONTIER: 2,
    ReadingStage.UPDATE: 3,
}

_SERIES_PATTERNS = (
    re.compile(r"^(?P<prefix>.+?)\s*[:：\-]\s*(?P<index>\d+)[、.：:\-]?\s*(?P<rest>.+)$", re.IGNORECASE),
    re.compile(
        r"^(?P<prefix>.+?)\s+(?:part|chapter|episode|lesson)\s*(?P<index>\d+)\b[:：\-]?\s*(?P<rest>.*)$",
        re.IGNORECASE,
    ),
)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
RAW_SUMMARY_MAX_LENGTH = 2000
CONTENT_EXCERPT_MAX_LENGTH = 5000


@dataclass
class WeeklyCandidate:
    article: Article
    tags: list[str]
    rule_topic_key: str
    rule_topic_label: str
    series_key: str | None
    series_index: int | None


def _monday_for_day(target: date) -> date:
    return target - timedelta(days=target.weekday())


def _article_statement():
    return select(Article).options(selectinload(Article.tags), selectinload(Article.source))


def _article_to_read(article: Article) -> ArticleRead:
    return ArticleRead(
        id=article.id or 0,
        source_id=article.source_id,
        source_name_snapshot=article.source_name_snapshot,
        title=article.title,
        url=article.url,
        published_at=article.published_at,
        author=article.author,
        raw_summary=article.raw_summary[:RAW_SUMMARY_MAX_LENGTH] if article.raw_summary else None,
        content_excerpt=article.content_excerpt[:CONTENT_EXCERPT_MAX_LENGTH] if article.content_excerpt else None,
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


def _slugify_text(value: str) -> str:
    lowered = value.strip().lower()
    normalized = _NON_ALNUM.sub("-", lowered)
    return normalized.strip("-") or "untitled"


def _extract_series_metadata(title: str) -> tuple[str | None, int | None, str | None]:
    stripped = title.strip()
    for pattern in _SERIES_PATTERNS:
        match = pattern.match(stripped)
        if match:
            prefix = match.group("prefix").strip()
            try:
                index = int(match.group("index"))
            except ValueError:
                index = None
            if prefix and index is not None:
                return _slugify_text(prefix), index, prefix
    return None, None, None


def _build_title_topic_label(title: str) -> str:
    condensed = " ".join(title.split())
    return condensed[:48] if condensed else "Reading track"


def _build_rule_topic_key(article: Article, tags: list[str]) -> tuple[str, str, str | None, int | None]:
    series_key, series_index, series_label = _extract_series_metadata(article.title)
    if series_key:
        return f"series:{series_key}", series_label or article.title, series_key, series_index

    if tags:
        primary_tag = tags[0]
        return f"tag:{_slugify_text(primary_tag)}", primary_tag, None, None

    source_name = article.source.name if article.source else article.source_name_snapshot
    source_part = _slugify_text(source_name or "source")
    label = _build_title_topic_label(article.title)
    return f"title:{source_part}:{_slugify_text(label)}", label, None, None


def _topic_selection_key(candidate: WeeklyCandidate) -> tuple:
    article = candidate.article
    published_timestamp = article.published_at.timestamp() if article.published_at else 0
    created_timestamp = article.created_at.timestamp()
    return (
        0 if article.is_core else 1,
        TOPIC_SELECTION_STAGE_WEIGHT.get(article.stage or ReadingStage.UPDATE, 99),
        article.source.priority if article.source else 9999,
        -published_timestamp,
        created_timestamp,
        article.title.lower(),
    )


def _sequence_key(candidate: WeeklyCandidate) -> tuple:
    article = candidate.article
    published_timestamp = article.published_at.timestamp() if article.published_at else 0
    update_timestamp = -published_timestamp if article.stage == ReadingStage.UPDATE else published_timestamp
    return (
        0 if candidate.series_index is not None else 1,
        candidate.series_index if candidate.series_index is not None else 999,
        SEQUENCE_STAGE_ORDER.get(article.stage or ReadingStage.UPDATE, 99),
        0 if article.is_core else 1,
        article.source.priority if article.source else 9999,
        update_timestamp,
        article.created_at.timestamp(),
        article.title.lower(),
    )


def build_weekly_candidates(articles: list[Article]) -> list[WeeklyCandidate]:
    candidates: list[WeeklyCandidate] = []
    for article in articles:
        if article.stage is None or article.status not in ACTIVE_STATUSES or not str(article.url).strip():
            continue

        tags = [tag.tag for tag in article.tags if isinstance(tag, ArticleTag) and tag.tag]
        rule_topic_key, rule_topic_label, series_key, series_index = _build_rule_topic_key(article, tags)
        candidates.append(
            WeeklyCandidate(
                article=article,
                tags=tags,
                rule_topic_key=rule_topic_key,
                rule_topic_label=rule_topic_label,
                series_key=series_key,
                series_index=series_index,
            )
        )
    return candidates


def get_ranked_weekly_candidate_articles(articles: list[Article]) -> list[Article]:
    candidates = build_weekly_candidates(articles)
    return [candidate.article for candidate in sorted(candidates, key=_topic_selection_key)]


def _topic_score(candidates: list[WeeklyCandidate]) -> tuple:
    strongest = min(_topic_selection_key(candidate) for candidate in candidates)
    core_count = sum(1 for candidate in candidates if candidate.article.is_core)
    non_update_count = sum(1 for candidate in candidates if candidate.article.stage != ReadingStage.UPDATE)
    return strongest + (-core_count, -non_update_count, -len(candidates))


def _get_sorted_topic_groups(candidates: list[WeeklyCandidate]) -> list[tuple[str, list[WeeklyCandidate]]]:
    grouped: dict[str, list[WeeklyCandidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.rule_topic_key].append(candidate)

    return sorted(grouped.items(), key=lambda item: _topic_score(item[1]))


def _ordered_candidates_for_topic(candidates: list[WeeklyCandidate]) -> list[WeeklyCandidate]:
    return sorted(candidates, key=_sequence_key)


def _build_fallback_selection(candidates: list[WeeklyCandidate]) -> dict:
    if not candidates:
        return {
            "primary_topic_key": None,
            "supplemental_topic_key": None,
            "primary_candidates": [],
            "supplemental_candidates": [],
            "metadata": [],
        }

    topic_groups = _get_sorted_topic_groups(candidates)
    primary_topic_key, primary_group = topic_groups[0]
    primary_candidates = _ordered_candidates_for_topic(primary_group)

    supplemental_topic_key: str | None = None
    supplemental_candidates: list[WeeklyCandidate] = []

    for topic_key, group in topic_groups[1:]:
        ordered_group = [candidate for candidate in _ordered_candidates_for_topic(group) if candidate.article.stage != ReadingStage.UPDATE]
        if ordered_group:
            supplemental_topic_key = topic_key
            supplemental_candidates = ordered_group
            break

    primary_ids = {candidate.article.id for candidate in primary_candidates}
    related_updates = [
        candidate
        for candidate in _ordered_candidates_for_topic(primary_group)
        if candidate.article.stage == ReadingStage.UPDATE and candidate.article.id not in primary_ids
    ]

    if supplemental_candidates:
        supplemental_candidates = supplemental_candidates[:3]
    if len(supplemental_candidates) < 3:
        supplemental_candidates.extend(related_updates[: max(0, 3 - len(supplemental_candidates))])
        if related_updates and supplemental_topic_key is None:
            supplemental_topic_key = primary_topic_key

    primary_candidates = primary_candidates[:5]
    seen_ids: set[int] = set()
    metadata: list[dict] = []

    for sequence_rank, candidate in enumerate(primary_candidates, start=1):
        article_id = candidate.article.id or 0
        if article_id in seen_ids:
            continue
        seen_ids.add(article_id)
        metadata.append(
            {
                "article_id": article_id,
                "topic_key": primary_topic_key,
                "track_type": "primary",
                "sequence_rank": sequence_rank,
                "reason": _fallback_reason(candidate, "primary"),
            }
        )

    filtered_supplemental: list[WeeklyCandidate] = []
    for candidate in supplemental_candidates:
        article_id = candidate.article.id or 0
        if article_id in seen_ids:
            continue
        seen_ids.add(article_id)
        filtered_supplemental.append(candidate)
        metadata.append(
            {
                "article_id": article_id,
                "topic_key": primary_topic_key
                if candidate.article.stage == ReadingStage.UPDATE and candidate.rule_topic_key == primary_topic_key
                else supplemental_topic_key or candidate.rule_topic_key,
                "track_type": "supplemental",
                "sequence_rank": len(filtered_supplemental),
                "reason": _fallback_reason(candidate, "supplemental"),
            }
        )

    return {
        "primary_topic_key": primary_topic_key,
        "supplemental_topic_key": supplemental_topic_key,
        "primary_candidates": primary_candidates,
        "supplemental_candidates": filtered_supplemental,
        "metadata": metadata,
    }


def _fallback_reason(candidate: WeeklyCandidate, track_type: str) -> str:
    stage_reason = {
        ReadingStage.FOUNDATION: "Foundational setup for the topic.",
        ReadingStage.CORE: "Core reading for the main idea.",
        ReadingStage.FRONTIER: "Advanced extension after the core material.",
        ReadingStage.UPDATE: "Recent update that keeps the topic current.",
    }.get(candidate.article.stage or ReadingStage.UPDATE, "Relevant reading for this week.")

    if candidate.series_index is not None:
        stage_reason = f"Part {candidate.series_index} in a continuing series."
    if track_type == "supplemental" and candidate.article.stage != ReadingStage.UPDATE:
        return f"Supplementary track that broadens this week's reading. {stage_reason}"
    return stage_reason


def select_weekly_plan_articles(articles: list[Article]) -> tuple[list[Article], list[Article]]:
    fallback = _build_fallback_selection(build_weekly_candidates(articles))
    return (
        [candidate.article for candidate in fallback["primary_candidates"]],
        [candidate.article for candidate in fallback["supplemental_candidates"]],
    )


def _validate_provider_plan(candidates: list[WeeklyCandidate], provider_plan: dict) -> dict | None:
    candidate_map = {candidate.article.id or 0: candidate for candidate in candidates}
    metadata_by_article: dict[int, dict] = {}

    for item in provider_plan.get("items", []):
        article_id = item["article_id"]
        candidate = candidate_map.get(article_id)
        if candidate is None:
            continue
        metadata_by_article[article_id] = {
            "article_id": article_id,
            "topic_key": item.get("topic_key") or candidate.rule_topic_key,
            "track_type": item["track_type"],
            "sequence_rank": max(1, int(item.get("sequence_rank") or 1)),
            "reason": item.get("reason") or _fallback_reason(candidate, item["track_type"]),
        }

    primary_topic_key = provider_plan.get("primary_topic_key")
    supplemental_topic_key = provider_plan.get("supplemental_topic_key")

    primary_candidates = [
        candidate
        for candidate in candidates
        if (candidate.article.id or 0) in metadata_by_article
        and metadata_by_article[candidate.article.id or 0]["track_type"] == "primary"
        and (
            not primary_topic_key
            or metadata_by_article[candidate.article.id or 0]["topic_key"] == primary_topic_key
        )
    ]

    if not primary_candidates:
        return None

    primary_candidates = sorted(
        primary_candidates,
        key=lambda candidate: metadata_by_article[candidate.article.id or 0]["sequence_rank"],
    )[:5]
    primary_ids = {candidate.article.id or 0 for candidate in primary_candidates}

    supplemental_candidates = [
        candidate
        for candidate in candidates
        if (candidate.article.id or 0) in metadata_by_article
        and metadata_by_article[candidate.article.id or 0]["track_type"] == "supplemental"
        and (candidate.article.id or 0) not in primary_ids
    ]

    valid_supplemental: list[WeeklyCandidate] = []
    for candidate in sorted(
        supplemental_candidates,
        key=lambda item: metadata_by_article[item.article.id or 0]["sequence_rank"],
    ):
        metadata = metadata_by_article[candidate.article.id or 0]
        topic_key = metadata["topic_key"]
        if candidate.article.stage == ReadingStage.UPDATE and topic_key != primary_topic_key:
            continue
        if supplemental_topic_key and candidate.article.stage != ReadingStage.UPDATE and topic_key != supplemental_topic_key:
            continue
        valid_supplemental.append(candidate)
        if len(valid_supplemental) >= 3:
            break

    normalized_metadata = []
    for article_id in [candidate.article.id or 0 for candidate in primary_candidates + valid_supplemental]:
        normalized_metadata.append(metadata_by_article[article_id])

    return {
        "primary_topic_key": primary_topic_key
        or (primary_candidates[0].rule_topic_key if primary_candidates else None),
        "supplemental_topic_key": supplemental_topic_key
        or (valid_supplemental[0].rule_topic_key if valid_supplemental else None),
        "primary_candidates": primary_candidates,
        "supplemental_candidates": valid_supplemental,
        "metadata": normalized_metadata,
        "generated_plan": provider_plan.get("generated_plan") or "",
        "generated_review": provider_plan.get("generated_review") or "",
    }


def _format_topic_label(topic_key: str | None, candidates: list[WeeklyCandidate]) -> str:
    if not topic_key:
        return "reading track"

    for candidate in candidates:
        if candidate.rule_topic_key == topic_key:
            return candidate.rule_topic_label

    normalized = topic_key.split(":", 1)[-1].replace("-", " ").strip()
    return normalized or "reading track"


def _build_fallback_plan_text(
    week_start: date,
    primary_candidates: list[WeeklyCandidate],
    supplemental_candidates: list[WeeklyCandidate],
    primary_topic_key: str | None,
    supplemental_topic_key: str | None,
    *,
    ui_language: str,
) -> tuple[str, str]:
    primary_label = _format_topic_label(primary_topic_key, primary_candidates)
    supplemental_label = _format_topic_label(supplemental_topic_key, supplemental_candidates)
    primary_lines = [
        f"{index}. {candidate.article.title}"
        for index, candidate in enumerate(primary_candidates, start=1)
    ]
    supplemental_lines = [
        f"{index}. {candidate.article.title}"
        for index, candidate in enumerate(supplemental_candidates, start=1)
    ]

    if ui_language == "en":
        generated_plan = "\n".join(
            [
                f"Week of {week_start.isoformat()}",
                f"Primary track: {primary_label}",
                *primary_lines,
                f"Supplemental track: {supplemental_label}" if supplemental_lines else "Supplemental track: none",
                *supplemental_lines,
            ]
        )
        generated_review = "\n".join(
            [
                f"Review the main line: {primary_label}.",
                "What idea became clearer after following the sequence?",
                "Which article should become the starting point for next week?",
            ]
        )
        return generated_plan, generated_review

    generated_plan = "\n".join(
        [
            f"{week_start.isoformat()} 这一周建议围绕“{primary_label}”推进主线阅读。",
            "主线顺序：",
            *primary_lines,
            "补充线：" if supplemental_lines else "本周没有单独补充线。",
            *(supplemental_lines if supplemental_lines else []),
            f"补充主题：{supplemental_label}" if supplemental_lines else "",
        ]
    ).strip()
    generated_review = "\n".join(
        [
            f"围绕“{primary_label}”做复盘：",
            "1. 哪一篇最适合作为这条线的起点，为什么？",
            "2. 哪个概念在主线推进中变得更清楚了？",
            "3. 下周应该延续这条线，还是切到新的主题？",
        ]
    )
    return generated_plan, generated_review


def _resolve_weekly_selection(session: Session, candidates: list[WeeklyCandidate], *, week_start: date) -> dict:
    fallback = _build_fallback_selection(candidates)
    settings = get_settings_payload(session)

    try:
        provider_plan = plan_weekly_curriculum_with_provider(
            session,
            week_start=week_start,
            candidates=[
                {
                    "id": candidate.article.id,
                    "title": candidate.article.title,
                    "source_name": candidate.article.source.name if candidate.article.source else candidate.article.source_name_snapshot,
                    "stage": candidate.article.stage.value if candidate.article.stage else None,
                    "difficulty": candidate.article.difficulty.value if candidate.article.difficulty else None,
                    "is_core": candidate.article.is_core,
                    "tags": candidate.tags,
                    "published_at": candidate.article.published_at.isoformat() if candidate.article.published_at else None,
                    "raw_summary": candidate.article.raw_summary,
                    "rule_topic_key": candidate.rule_topic_key,
                    "series_key": candidate.series_key,
                    "series_index": candidate.series_index,
                }
                for candidate in candidates
            ],
        )
        validated = _validate_provider_plan(candidates, provider_plan)
        if validated is not None:
            return validated
    except ProviderNotConfiguredError:
        pass
    except Exception:
        pass

    generated_plan, generated_review = _build_fallback_plan_text(
        week_start,
        fallback["primary_candidates"],
        fallback["supplemental_candidates"],
        fallback["primary_topic_key"],
        fallback["supplemental_topic_key"],
        ui_language=settings.ui_language,
    )
    fallback["generated_plan"] = generated_plan
    fallback["generated_review"] = generated_review
    return fallback


def _load_articles_for_review(session: Session, review: WeeklyReview) -> dict[int, Article]:
    article_ids = list(dict.fromkeys(review.primary_article_ids + review.supplemental_article_ids))
    if not article_ids:
        return {}
    articles = session.exec(
        _article_statement().where(Article.id.in_(article_ids))
    ).all()
    return {article.id or 0: article for article in articles}


def _build_planned_articles(
    article_ids: list[int],
    topic_key: str | None,
    track_type: str,
    article_map: dict[int, Article],
    metadata_map: dict[int, dict],
) -> list[WeeklyPlannedArticleRead]:
    planned: list[WeeklyPlannedArticleRead] = []
    for sequence_rank, article_id in enumerate(article_ids, start=1):
        article = article_map.get(article_id)
        if article is None:
            continue
        metadata = metadata_map.get(article_id, {})
        planned.append(
            WeeklyPlannedArticleRead(
                article=_article_to_read(article),
                topic_key=metadata.get("topic_key") or topic_key,
                track_type=metadata.get("track_type") or track_type,
                sequence_rank=int(metadata.get("sequence_rank") or sequence_rank),
                reason=str(metadata.get("reason") or "").strip(),
            )
        )
    return planned


def weekly_review_to_read(session: Session, review: WeeklyReview) -> WeeklyReviewRead:
    article_map = _load_articles_for_review(session, review)
    metadata_items = []
    for item in review.article_plan_metadata or []:
        if not isinstance(item, dict) or not item.get("article_id"):
            continue
        metadata_items.append(
            WeeklyPlannedArticleMetadata(
                article_id=int(item.get("article_id") or 0),
                topic_key=item.get("topic_key"),
                track_type=str(item.get("track_type") or "skip"),
                sequence_rank=int(item.get("sequence_rank") or 0),
                reason=str(item.get("reason") or "").strip(),
            )
        )
    metadata_map = {item.article_id: item.model_dump() for item in metadata_items}

    return WeeklyReviewRead(
        id=review.id or 0,
        week_start=review.week_start,
        generated_plan=review.generated_plan,
        generated_review=review.generated_review,
        primary_article_ids=review.primary_article_ids,
        supplemental_article_ids=review.supplemental_article_ids,
        primary_topic_key=review.primary_topic_key,
        supplemental_topic_key=review.supplemental_topic_key,
        article_plan_metadata=metadata_items,
        primary_articles=_build_planned_articles(
            review.primary_article_ids,
            review.primary_topic_key,
            "primary",
            article_map,
            metadata_map,
        ),
        supplemental_articles=_build_planned_articles(
            review.supplemental_article_ids,
            review.supplemental_topic_key,
            "supplemental",
            article_map,
            metadata_map,
        ),
        created_at=review.created_at,
    )


def list_weekly_reviews(session: Session) -> list[WeeklyReviewRead]:
    reviews = session.exec(select(WeeklyReview).order_by(WeeklyReview.week_start.desc())).all()
    return [weekly_review_to_read(session, review) for review in reviews]


def get_current_weekly_review(session: Session, *, today: date | None = None) -> WeeklyReviewRead | None:
    week_start = _monday_for_day(today or date.today())
    review = session.exec(select(WeeklyReview).where(WeeklyReview.week_start == week_start)).first()
    if review is None:
        return None
    return weekly_review_to_read(session, review)


def generate_weekly_review(session: Session, *, today: date | None = None) -> WeeklyReviewRead:
    week_start = _monday_for_day(today or date.today())

    articles = session.exec(
        _article_statement()
        .where(Article.stage.is_not(None))
        .where(Article.status.in_(list(ACTIVE_STATUSES)))
    ).all()

    candidates = build_weekly_candidates(articles)
    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No eligible articles are available for this week's plan yet.",
        )

    selection = _resolve_weekly_selection(session, candidates, week_start=week_start)
    primary_articles = [candidate.article for candidate in selection["primary_candidates"]]
    supplemental_articles = [candidate.article for candidate in selection["supplemental_candidates"]]

    review = session.exec(select(WeeklyReview).where(WeeklyReview.week_start == week_start)).first()
    if review is None:
        review = WeeklyReview(week_start=week_start)
        session.add(review)

    review.generated_plan = selection["generated_plan"]
    review.generated_review = selection["generated_review"]
    review.primary_article_ids = [article.id or 0 for article in primary_articles]
    review.supplemental_article_ids = [article.id or 0 for article in supplemental_articles]
    review.primary_topic_key = selection["primary_topic_key"]
    review.supplemental_topic_key = selection["supplemental_topic_key"]
    review.article_plan_metadata = selection["metadata"]
    session.add(review)
    session.commit()
    session.refresh(review)

    return weekly_review_to_read(session, review)
