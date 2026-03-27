from fastapi import HTTPException
from sqlmodel import select

from app.models import Article, ArticleTag, ReadingStage, ReadingStatus
from app.services.provider_service import ProviderNotConfiguredError
from app.services.weekly_service import (
    build_weekly_candidates,
    generate_weekly_review,
)


def test_generate_weekly_review_requires_candidate_articles(session) -> None:
    try:
        generate_weekly_review(session)
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "No eligible articles are available for this week's plan yet."


def test_build_weekly_candidates_excludes_completed_articles(session) -> None:
    session.add(
        Article(
            title="Reviewed Article",
            url="https://example.com/reviewed",
            stage=ReadingStage.CORE,
            status=ReadingStatus.REVIEWED,
        )
    )
    session.add(
        Article(
            title="Planned Article",
            url="https://example.com/planned",
            stage=ReadingStage.CORE,
            status=ReadingStatus.PLANNED,
        )
    )
    session.commit()

    articles = session.exec(select(Article)).all()
    candidates = build_weekly_candidates(articles)

    assert len(candidates) == 1
    assert candidates[0].article.title == "Planned Article"


def test_generate_weekly_review_falls_back_without_provider(session, monkeypatch) -> None:
    article = Article(
        title="Core Reading",
        url="https://example.com/core-reading",
        stage=ReadingStage.CORE,
        status=ReadingStatus.PLANNED,
        is_core=True,
        raw_summary="Core summary",
    )
    session.add(article)
    session.commit()
    session.refresh(article)

    monkeypatch.setattr(
        "app.services.weekly_service.plan_weekly_curriculum_with_provider",
        lambda *args, **kwargs: (_ for _ in ()).throw(ProviderNotConfiguredError()),
    )

    review = generate_weekly_review(session)

    assert review.primary_article_ids == [article.id]
    assert review.primary_articles[0].article.id == article.id
    assert "Core Reading" in (review.generated_plan or "")
    assert review.generated_review


def test_generate_weekly_review_keeps_series_order_in_fallback(session, monkeypatch) -> None:
    first = Article(
        title="Transformer升级之路：1、Sinusoidal位置编码追根溯源",
        url="https://example.com/rope-1",
        stage=ReadingStage.FOUNDATION,
        status=ReadingStatus.PLANNED,
        is_core=True,
    )
    second = Article(
        title="Transformer升级之路：2、博采众长的旋转式位置编码",
        url="https://example.com/rope-2",
        stage=ReadingStage.CORE,
        status=ReadingStatus.PLANNED,
        is_core=True,
    )
    session.add(first)
    session.add(second)
    session.commit()
    session.refresh(first)
    session.refresh(second)

    monkeypatch.setattr(
        "app.services.weekly_service.plan_weekly_curriculum_with_provider",
        lambda *args, **kwargs: (_ for _ in ()).throw(ProviderNotConfiguredError()),
    )

    review = generate_weekly_review(session)

    assert review.primary_article_ids == [first.id, second.id]


def test_generate_weekly_review_uses_provider_track_selection(session, monkeypatch) -> None:
    first = Article(
        title="First Article",
        url="https://example.com/first-article",
        stage=ReadingStage.CORE,
        status=ReadingStatus.PLANNED,
        is_core=True,
        raw_summary="First summary",
    )
    second = Article(
        title="Second Article",
        url="https://example.com/second-article",
        stage=ReadingStage.FOUNDATION,
        status=ReadingStatus.PLANNED,
        raw_summary="Second summary",
    )
    third = Article(
        title="Third Article",
        url="https://example.com/third-article",
        stage=ReadingStage.UPDATE,
        status=ReadingStatus.PLANNED,
        raw_summary="Third summary",
    )
    session.add(first)
    session.add(second)
    session.add(third)
    session.commit()
    session.refresh(first)
    session.refresh(second)
    session.refresh(third)
    session.add(ArticleTag(article_id=first.id, tag="transformer"))
    session.add(ArticleTag(article_id=second.id, tag="transformer"))
    session.add(ArticleTag(article_id=third.id, tag="transformer"))
    session.commit()

    monkeypatch.setattr(
        "app.services.weekly_service.plan_weekly_curriculum_with_provider",
        lambda *args, **kwargs: {
            "primary_topic_key": "tag:transformer",
            "supplemental_topic_key": "tag:transformer",
            "items": [
                {
                    "article_id": second.id,
                    "topic_key": "tag:transformer",
                    "track_type": "primary",
                    "sequence_rank": 1,
                    "reason": "Start here.",
                },
                {
                    "article_id": first.id,
                    "topic_key": "tag:transformer",
                    "track_type": "primary",
                    "sequence_rank": 2,
                    "reason": "Then go deeper.",
                },
                {
                    "article_id": third.id,
                    "topic_key": "tag:transformer",
                    "track_type": "supplemental",
                    "sequence_rank": 1,
                    "reason": "Use as an update.",
                },
            ],
            "generated_plan": "Plan",
            "generated_review": "Review",
        },
    )

    review = generate_weekly_review(session)

    assert review.primary_article_ids == [second.id, first.id]
    assert review.supplemental_article_ids == [third.id]
    assert review.primary_topic_key == "tag:transformer"
    assert review.primary_articles[0].reason == "Start here."
