from app.models import Article, Source


def test_create_source_rejects_duplicate_rss_url(client) -> None:
    payload = {
        "name": "Hugging Face Blog",
        "homepage_url": "https://huggingface.co/blog",
        "rss_url": "https://huggingface.co/blog/feed.xml",
        "category": "AIGC",
        "language": "en",
        "priority": 10,
        "is_active": True,
    }

    first = client.post("/api/sources", json=payload)
    second = client.post("/api/sources", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["message"] == "An RSS source with the same URL already exists."


def test_delete_source_keeps_existing_articles(client, session) -> None:
    source = Source(
        name="Lil'Log",
        rss_url="https://lilianweng.github.io/index.xml",
        homepage_url="https://lilianweng.github.io/",
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

    monkeypatch.setattr("app.services.source_service.fetch_feed_content", lambda _: sample_feed)

    first = client.post(f"/api/sources/{source.id}/fetch")
    second = client.post(f"/api/sources/{source.id}/fetch")

    assert first.status_code == 200
    assert first.json()["inserted_count"] == 1
    assert second.status_code == 200
    assert second.json()["inserted_count"] == 0
    assert second.json()["deduplicated_count"] == 1


def test_test_source_endpoint_returns_feed_metadata(client, session, monkeypatch) -> None:
    source = Source(name="Science Space", rss_url="https://kexue.fm/feed")
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
