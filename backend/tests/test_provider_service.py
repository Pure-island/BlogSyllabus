from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError

from app.models import Article, Source
from app.services.provider_service import analyze_article_with_provider


def _build_fake_client(create_callable):
    return SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=create_callable,
            )
        )
    )


def test_analyze_article_retries_and_succeeds(monkeypatch) -> None:
    request = httpx.Request("POST", "https://provider.example/v1/chat/completions")
    calls = {"count": 0}

    def fake_create(**kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise APITimeoutError(request=request)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            '{"tags":["llm"],"difficulty":"beginner","stage":"foundation",'
                            '"estimated_minutes":8,"one_sentence_summary":"Intro",'
                            '"checkpoint_questions":["What matters?"],"core_score":0.8,'
                            '"core_reason":"Good primer"}'
                        )
                    )
                )
            ]
        )

    monkeypatch.setattr(
        "app.services.provider_service.get_provider_client",
        lambda session: (
            _build_fake_client(fake_create),
            SimpleNamespace(llm_model="gpt-4.1-mini"),
        ),
    )
    monkeypatch.setattr("app.services.provider_service.time.sleep", lambda seconds: None)

    result = analyze_article_with_provider(
        None,
        Article(title="Retryable analysis", raw_summary="Summary"),
        Source(name="Example Source", rss_url="https://example.com/feed.xml"),
    )

    assert calls["count"] == 2
    assert result["tags"] == ["llm"]
    assert result["stage"] == "foundation"
    assert result["core_score"] == 0.8


def test_analyze_article_raises_after_retry_budget(monkeypatch) -> None:
    request = httpx.Request("POST", "https://provider.example/v1/chat/completions")
    calls = {"count": 0}

    def fake_create(**kwargs):
        calls["count"] += 1
        raise APIConnectionError(message="temporary outage", request=request)

    monkeypatch.setattr(
        "app.services.provider_service.get_provider_client",
        lambda session: (
            _build_fake_client(fake_create),
            SimpleNamespace(llm_model="gpt-4.1-mini"),
        ),
    )
    monkeypatch.setattr("app.services.provider_service.time.sleep", lambda seconds: None)

    with pytest.raises(RuntimeError) as exc:
        analyze_article_with_provider(
            None,
            Article(title="Retryable analysis", raw_summary="Summary"),
            Source(name="Example Source", rss_url="https://example.com/feed.xml"),
        )

    assert calls["count"] == 3
    assert "failed after 3 attempts" in str(exc.value)
