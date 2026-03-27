from fastapi import HTTPException

from app.models import JobType, Source, SourceType
from app.services.import_service import create_fetch_active_job, create_fetch_single_source_job


def test_create_fetch_active_job_includes_only_active_rss_sources(session) -> None:
    rss_source = Source(
        name="RSS Source",
        homepage_url="https://example.com",
        rss_url="https://example.com/feed.xml",
        source_type=SourceType.RSS,
        is_active=True,
    )
    manual_source = Source(
        name="Manual Source",
        homepage_url="https://manual.example.com",
        rss_url=None,
        source_type=SourceType.MANUAL,
        is_active=True,
    )
    paused_rss_source = Source(
        name="Paused RSS Source",
        homepage_url="https://paused.example.com",
        rss_url="https://paused.example.com/feed.xml",
        source_type=SourceType.RSS,
        is_active=False,
    )
    session.add(rss_source)
    session.add(manual_source)
    session.add(paused_rss_source)
    session.commit()

    job = create_fetch_active_job(session)

    assert job.job_type == JobType.FETCH_ACTIVE_SOURCES
    assert job.total_sources == 1
    assert job.payload["source_ids"] == [rss_source.id]


def test_create_fetch_single_source_job_rejects_manual_sources(session) -> None:
    manual_source = Source(
        name="Manual Source",
        homepage_url="https://manual.example.com",
        rss_url=None,
        source_type=SourceType.MANUAL,
        is_active=True,
    )
    session.add(manual_source)
    session.commit()

    try:
        create_fetch_single_source_job(session, manual_source.id or 0)
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "RSS is not configured for this source."
    else:  # pragma: no cover
        raise AssertionError("Expected manual source fetch to be rejected.")
