from app.models import Source
from app.services.rss import normalize_entries, parse_feed_content

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
