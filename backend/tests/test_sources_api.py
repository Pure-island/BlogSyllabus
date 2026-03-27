from app.models import Article, Source, SourceType


def test_create_source_rejects_duplicate_rss_url(client) -> None:
    payload = {
        "name": "Hugging Face Blog",
        "homepage_url": "https://huggingface.co/blog",
        "rss_url": "https://huggingface.co/blog/feed.xml",
        "source_type": "rss",
        "language": "en",
        "priority": 10,
        "is_active": True,
    }

    first = client.post("/api/sources", json=payload)
    second = client.post("/api/sources", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["message"] == "An RSS source with the same URL already exists."


def test_create_manual_source_without_rss_url(client) -> None:
    response = client.post(
        "/api/sources",
        json={
            "name": "Curated Notes",
            "homepage_url": "https://example.com/notes",
            "rss_url": None,
            "source_type": "manual",
            "language": "zh-CN",
            "priority": 40,
            "is_active": True,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["rss_url"] is None
    assert payload["source_type"] == "manual"


def test_upgrade_manual_source_to_rss_keeps_same_source_id(client, session) -> None:
    source = Source(
        name="Manual Source",
        homepage_url="https://example.com/manual",
        rss_url=None,
        source_type=SourceType.MANUAL,
    )
    session.add(source)
    session.commit()
    session.refresh(source)

    article = Article(
        source_id=source.id,
        source_name_snapshot=source.name,
        title="Imported From Text",
        url="https://example.com/articles/manual-import",
    )
    session.add(article)
    session.commit()

    response = client.patch(
        f"/api/sources/{source.id}",
        json={
            "rss_url": "https://example.com/feed.xml",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == source.id
    assert payload["source_type"] == "rss"
    assert payload["rss_url"] == "https://example.com/feed.xml"

    session.refresh(article)
    assert article.source_id == source.id


def test_delete_source_keeps_existing_articles(client, session) -> None:
    source = Source(
        name="Lil'Log",
        rss_url="https://lilianweng.github.io/index.xml",
        homepage_url="https://lilianweng.github.io/",
        source_type=SourceType.RSS,
    )
    session.add(source)
    session.commit()
    session.refresh(source)

    article = Article(
        source_id=source.id,
        source_name_snapshot=source.name,
        title="Agent Foundations",
        url="https://example.com/agent-foundations",
    )
    session.add(article)
    session.commit()
    session.refresh(article)

    response = client.delete(f"/api/sources/{source.id}")

    assert response.status_code == 204
    session.refresh(article)
    assert article.source_id is None
    assert article.source_name_snapshot == "Lil'Log"


def test_fetch_source_deduplicates_articles(client, session, monkeypatch) -> None:
    source = Source(
        name="BAIR Blog",
        rss_url="https://bair.berkeley.edu/blog/feed.xml",
        homepage_url="https://bair.berkeley.edu/blog/",
        source_type=SourceType.RSS,
    )
    session.add(source)
    session.commit()
    session.refresh(source)

    sample_feed = """<?xml version="1.0" encoding="UTF-8" ?>
    <rss version="2.0">
      <channel>
        <title>BAIR Blog</title>
        <item>
          <title>One Article</title>
          <link>https://example.com/one-article</link>
          <description>One article summary.</description>
        </item>
      </channel>
    </rss>"""

    monkeypatch.setattr("app.services.import_service.fetch_feed_content", lambda _: sample_feed)

    first = client.post(f"/api/sources/{source.id}/fetch")
    second = client.post(f"/api/sources/{source.id}/fetch")

    assert first.status_code == 200
    assert first.json()["inserted_count"] == 1
    assert second.status_code == 200
    assert second.json()["inserted_count"] == 0
    assert second.json()["deduplicated_count"] == 1


def test_manual_source_rss_actions_are_rejected(client, session) -> None:
    source = Source(
        name="Manual Source",
        homepage_url="https://example.com/manual",
        rss_url=None,
        source_type=SourceType.MANUAL,
    )
    session.add(source)
    session.commit()
    session.refresh(source)

    response = client.post(f"/api/sources/{source.id}/test")

    assert response.status_code == 400
    assert response.json()["message"] == "RSS is not configured for this source."


def test_test_source_endpoint_returns_feed_metadata(client, session, monkeypatch) -> None:
    source = Source(name="Science Space", rss_url="https://kexue.fm/feed", source_type=SourceType.RSS)
    session.add(source)
    session.commit()
    session.refresh(source)

    monkeypatch.setattr(
        "app.services.source_service.validate_feed",
        lambda _: {"feed_title": "Science Space", "entry_count": 12},
    )

    response = client.post(f"/api/sources/{source.id}/test")

    assert response.status_code == 200
    assert response.json()["feed_title"] == "Science Space"
    assert response.json()["entry_count"] == 12


def test_bulk_import_job_is_created_for_rss_sources_only(client, session) -> None:
    rss_source = Source(
        name="Example Feed",
        rss_url="https://example.com/feed.xml",
        homepage_url="https://example.com",
        source_type=SourceType.RSS,
        is_active=True,
    )
    manual_source = Source(
        name="Manual Feed",
        homepage_url="https://manual.example.com",
        rss_url=None,
        source_type=SourceType.MANUAL,
        is_active=True,
    )
    session.add(rss_source)
    session.add(manual_source)
    session.commit()

    response = client.post("/api/imports/sources/fetch-active")

    assert response.status_code == 202
    jobs_response = client.get("/api/imports/jobs")
    assert jobs_response.status_code == 200
    assert len(jobs_response.json()) == 1
    job = jobs_response.json()[0]
    assert job["job_type"] == "fetch_active_sources"
    assert job["total_sources"] == 1
    assert len(job["items"]) == 1
    assert job["items"][0]["source_id"] == rss_source.id
