from app.models import Article, Source, SourceType


def test_import_preview_parses_markdown_and_plain_lines(client) -> None:
    response = client.post(
        "/api/articles/import-preview",
        json={
            "raw_text": "\n".join(
                [
                    "[Intro to Agents](https://example.com/agents-intro)",
                    "Planning in LLM Agents https://example.com/planning-agents",
                ]
            ),
            "use_llm_fallback": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["importable_count"] == 2
    assert payload["duplicate_count"] == 0
    assert payload["invalid_count"] == 0


def test_import_preview_parses_csv_input(client) -> None:
    response = client.post(
        "/api/articles/import-preview",
        json={
            "raw_text": "title,url,author\nArticle One,https://example.com/article-one,Alice",
            "use_llm_fallback": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["importable_count"] == 1
    assert payload["parsed_items"][0]["title"] == "Article One"


def test_import_batch_can_create_manual_source_and_insert_articles(client, session) -> None:
    response = client.post(
        "/api/articles/import-batch",
        json={
            "items": [
                {
                    "title": "Manual Import",
                    "url": "https://example.com/manual-import",
                    "author": "Alice",
                    "published_at": None,
                    "raw_summary": "Summary",
                    "content_excerpt": "Summary",
                    "source_name_snapshot": None,
                }
            ],
            "source_id": None,
            "new_source": {
                "name": "Curated Import",
                "homepage_url": "https://example.com/curated",
                "language": "en",
                "priority": 20,
                "is_active": True,
            },
            "analyze_after_import": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["inserted_count"] == 1
    assert payload["source_id"] is not None

    source = session.get(Source, payload["source_id"])
    assert source is not None
    assert source.source_type == SourceType.MANUAL
    assert source.rss_url is None


def test_import_batch_skips_duplicate_urls(client, session) -> None:
    existing = Article(
        title="Existing",
        url="https://example.com/existing",
    )
    session.add(existing)
    session.commit()

    response = client.post(
        "/api/articles/import-batch",
        json={
            "items": [
                {
                    "title": "Existing",
                    "url": "https://example.com/existing",
                    "author": None,
                    "published_at": None,
                    "raw_summary": None,
                    "content_excerpt": None,
                    "source_name_snapshot": None,
                }
            ],
            "source_id": None,
            "new_source": None,
            "analyze_after_import": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["inserted_count"] == 0
    assert payload["duplicate_count"] == 1


def test_import_batch_without_provider_still_imports_when_analysis_requested(client) -> None:
    response = client.post(
        "/api/articles/import-batch",
        json={
            "items": [
                {
                    "title": "Analyze Later",
                    "url": "https://example.com/analyze-later",
                    "author": None,
                    "published_at": None,
                    "raw_summary": None,
                    "content_excerpt": None,
                    "source_name_snapshot": None,
                }
            ],
            "source_id": None,
            "new_source": None,
            "analyze_after_import": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["inserted_count"] == 1
    assert payload["analyze_job_id"] is None
