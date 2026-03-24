from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import httpx

from app.core.config import get_settings
from app.models import Source

settings = get_settings()


class FeedError(ValueError):
    pass


def fetch_feed_content(url: str) -> str:
    with httpx.Client(timeout=settings.request_timeout_seconds, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def parse_feed_content(content: str) -> feedparser.FeedParserDict:
    parsed = feedparser.parse(content)
    if getattr(parsed, "bozo", False) and not parsed.entries:
        exception = getattr(parsed, "bozo_exception", None)
        raise FeedError(str(exception) if exception else "Unable to parse RSS feed.")
    if not parsed.entries:
        raise FeedError("RSS feed has no entries.")
    return parsed


def validate_feed(url: str) -> dict[str, Any]:
    parsed = parse_feed_content(fetch_feed_content(url))
    return {
        "feed_title": parsed.feed.get("title"),
        "entry_count": len(parsed.entries),
    }


def _parse_published_at(entry: feedparser.FeedParserDict) -> datetime | None:
    published = entry.get("published") or entry.get("updated")
    if not published:
        return None
    try:
        return parsedate_to_datetime(published)
    except (TypeError, ValueError):
        return None


def normalize_entries(source: Source, content: str) -> list[dict[str, Any]]:
    parsed = parse_feed_content(content)
    normalized_entries: list[dict[str, Any]] = []

    for entry in parsed.entries:
        url = entry.get("link")
        title = entry.get("title")
        if not url or not title:
            continue

        summary = entry.get("summary") or entry.get("description")
        normalized_entries.append(
            {
                "source_id": source.id,
                "source_name_snapshot": source.name,
                "title": title.strip(),
                "url": url.strip(),
                "published_at": _parse_published_at(entry),
                "author": entry.get("author"),
                "raw_summary": summary.strip() if isinstance(summary, str) else None,
                "content_excerpt": summary.strip()[:800] if isinstance(summary, str) else None,
            }
        )

    return normalized_entries
