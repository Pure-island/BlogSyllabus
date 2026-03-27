from app.models import Article, ReadingStage, ReadingStatus
from app.services.article_service import generate_today
from app.services.weekly_service import generate_weekly_review


def test_generate_today_prefers_current_weekly_review_articles(session, monkeypatch) -> None:
    weekly_primary = Article(
        title="Weekly Primary",
        url="https://example.com/weekly-primary",
        stage=ReadingStage.CORE,
        status=ReadingStatus.PLANNED,
        is_core=True,
    )
    weekly_secondary = Article(
        title="Weekly Secondary",
        url="https://example.com/weekly-secondary",
        stage=ReadingStage.FOUNDATION,
        status=ReadingStatus.PLANNED,
    )
    fallback = Article(
        title="Fallback Article",
        url="https://example.com/fallback-article",
        stage=ReadingStage.FOUNDATION,
        status=ReadingStatus.PLANNED,
    )
    session.add(weekly_primary)
    session.add(weekly_secondary)
    session.add(fallback)
    session.commit()
    session.refresh(weekly_primary)
    session.refresh(weekly_secondary)

    monkeypatch.setattr(
        "app.services.weekly_service.plan_weekly_curriculum_with_provider",
        lambda *args, **kwargs: {
            "primary_topic_key": "tag:main",
            "supplemental_topic_key": "tag:support",
            "items": [
                {
                    "article_id": weekly_primary.id,
                    "topic_key": "tag:main",
                    "track_type": "primary",
                    "sequence_rank": 1,
                    "reason": "Primary first.",
                },
                {
                    "article_id": weekly_secondary.id,
                    "topic_key": "tag:support",
                    "track_type": "supplemental",
                    "sequence_rank": 1,
                    "reason": "Supplement here.",
                },
            ],
            "generated_plan": "Plan",
            "generated_review": "Review",
        },
    )

    review = generate_weekly_review(session)
    monkeypatch.setattr("app.services.article_service.get_current_weekly_review", lambda db_session: review)
    today = generate_today(session)

    assert today.primary_article is not None
    assert today.secondary_article is not None
    assert today.primary_article.id == weekly_primary.id
    assert today.secondary_article.id == weekly_secondary.id


def test_generate_today_falls_back_to_next_primary_when_no_supplemental(session, monkeypatch) -> None:
    first = Article(
        title="Primary One",
        url="https://example.com/primary-1",
        stage=ReadingStage.FOUNDATION,
        status=ReadingStatus.REVIEWED,
        is_core=True,
    )
    second = Article(
        title="Primary Two",
        url="https://example.com/primary-2",
        stage=ReadingStage.CORE,
        status=ReadingStatus.PLANNED,
        is_core=True,
    )
    third = Article(
        title="Primary Three",
        url="https://example.com/primary-3",
        stage=ReadingStage.FRONTIER,
        status=ReadingStatus.PLANNED,
    )
    session.add(first)
    session.add(second)
    session.add(third)
    session.commit()
    session.refresh(first)
    session.refresh(second)
    session.refresh(third)

    review = type(
        "Review",
        (),
        {
            "primary_article_ids": [first.id, second.id, third.id],
            "supplemental_article_ids": [],
        },
    )()

    monkeypatch.setattr("app.services.article_service.get_current_weekly_review", lambda db_session: review)
    today = generate_today(session)

    assert today.primary_article is not None
    assert today.secondary_article is not None
    assert today.primary_article.id == second.id
    assert today.secondary_article.id == third.id


def test_generate_today_clamps_oversized_raw_summary(session, monkeypatch) -> None:
    article = Article(
        title="Long Summary",
        url="https://example.com/long-summary",
        stage=ReadingStage.CORE,
        status=ReadingStatus.PLANNED,
        raw_summary="x" * 2600,
    )
    session.add(article)
    session.commit()
    session.refresh(article)

    monkeypatch.setattr("app.services.article_service.get_current_weekly_review", lambda db_session: None)
    today = generate_today(session)

    assert today.primary_article is not None
    assert len(today.primary_article.raw_summary or "") == 2000
