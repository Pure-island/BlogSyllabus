import httpx
import pytest

from app.models import Source
from app.services.rss import FeedError, fetch_feed_content, normalize_entries, parse_feed_content

SAMPLE_FEED = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>Sample Feed</title>
    <item>
      <title>First Post</title>
      <link>https://example.com/posts/1</link>
      <description>Intro to agent systems.</description>
      <pubDate>Tue, 25 Mar 2025 10:00:00 GMT</pubDate>
      <author>Jane Doe</author>
    </item>
  </channel>
</rss>
"""


def test_parse_feed_content_returns_entries() -> None:
    parsed = parse_feed_content(SAMPLE_FEED)
    assert parsed.feed["title"] == "Sample Feed"
    assert len(parsed.entries) == 1


def test_normalize_entries_maps_source_fields() -> None:
    source = Source(id=1, name="Sample Source", rss_url="https://example.com/feed.xml")
    entries = normalize_entries(source, SAMPLE_FEED)

    assert len(entries) == 1
    assert entries[0]["source_id"] == 1
    assert entries[0]["source_name_snapshot"] == "Sample Source"
    assert entries[0]["title"] == "First Post"
    assert entries[0]["url"] == "https://example.com/posts/1"


def test_fetch_feed_content_surfaces_tls_eof_as_feed_error(monkeypatch) -> None:
    class BrokenClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def get(self, url: str):
            raise httpx.ConnectError(
                "[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1028)"
            )

    monkeypatch.setattr("app.services.rss.httpx.Client", BrokenClient)

    with pytest.raises(FeedError) as exc:
        fetch_feed_content("https://example.com/feed.xml")

    assert "closed the TLS connection unexpectedly" in str(exc.value)
