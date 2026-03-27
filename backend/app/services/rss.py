from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urldefrag

import feedparser
import httpx

from app.core.config import get_settings
from app.models import Source

settings = get_settings()
RAW_SUMMARY_MAX_LENGTH = 2000
CONTENT_EXCERPT_MAX_LENGTH = 5000


class FeedError(ValueError):
    pass


DEFAULT_FEED_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}

def _canonicalize_url(url: str) -> str:
    clean, _ = urldefrag(url.strip())
    return clean


def _parse_published_at(entry: feedparser.FeedParserDict) -> datetime | None:
    published = entry.get("published") or entry.get("updated")
    if not published:
        return None
    try:
        return parsedate_to_datetime(published)
    except (TypeError, ValueError):
        return None


def _parse_lastmod(value: str | None) -> datetime | None:
    if not value:
        return None

    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def fetch_text_content(url: str) -> str:
    transport = httpx.HTTPTransport(retries=2)

    try:
        with httpx.Client(
            timeout=settings.request_timeout_seconds,
            follow_redirects=True,
            headers=DEFAULT_FEED_HEADERS,
            transport=transport,
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as exc:
        raise FeedError(f"Failed to fetch URL: {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        message = str(exc)
        if "UNEXPECTED_EOF_WHILE_READING" in message:
            raise FeedError(
                "The remote server closed the TLS connection unexpectedly."
            ) from exc
        raise FeedError(f"Failed to fetch URL: {message}") from exc


def fetch_feed_content(url: str) -> str:
    return fetch_text_content(url)


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


def normalize_entries(source: Source, content: str) -> list[dict[str, Any]]:
    parsed = parse_feed_content(content)
    normalized_entries: list[dict[str, Any]] = []

    for entry in parsed.entries:
        url = entry.get("link")
        title = entry.get("title")
        if not url or not title:
            continue

        summary = entry.get("summary") or entry.get("description")
        normalized_summary = summary.strip() if isinstance(summary, str) else None
        normalized_entries.append(
            {
                "source_id": source.id,
                "source_name_snapshot": source.name,
                "title": title.strip(),
                "url": _canonicalize_url(url),
                "published_at": _parse_published_at(entry),
                "author": entry.get("author"),
                "raw_summary": normalized_summary[:RAW_SUMMARY_MAX_LENGTH] if normalized_summary else None,
                "content_excerpt": normalized_summary[: min(800, CONTENT_EXCERPT_MAX_LENGTH)] if normalized_summary else None,
            }
        )

    return normalized_entries
