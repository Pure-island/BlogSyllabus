from __future__ import annotations

import json
import time
from datetime import date, datetime

from fastapi import HTTPException, status
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)
from sqlmodel import Session

from app.models import Article, Source
from app.schemas import ArticleImportCandidate, SettingsPayload
from app.services.settings_service import get_settings_payload


class ProviderNotConfiguredError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="LLM provider is not configured.",
        )


PROVIDER_MAX_ATTEMPTS = 3
PROVIDER_RETRY_DELAY_SECONDS = 0.6


def _build_provider_client(settings: SettingsPayload) -> OpenAI:
    return OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url.strip() or None,
    )


def _validate_connection_test_settings(settings: SettingsPayload) -> SettingsPayload:
    if not settings.llm_api_key.strip() or not settings.llm_model.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider API key and model are required for connection testing.",
        )
    return settings


def ensure_provider_settings(session: Session) -> SettingsPayload:
    settings = get_settings_payload(session)
    if not settings.llm_enabled or not settings.llm_api_key or not settings.llm_model:
        raise ProviderNotConfiguredError()
    return settings


def get_provider_client(session: Session) -> tuple[OpenAI, SettingsPayload]:
    settings = ensure_provider_settings(session)
    client = _build_provider_client(settings)
    return client, settings


def _is_retryable_provider_error(exc: Exception) -> bool:
    if isinstance(exc, (APITimeoutError, APIConnectionError, RateLimitError, InternalServerError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code in {408, 409, 425, 429} or exc.status_code >= 500
    if isinstance(exc, ValueError):
        return True
    if isinstance(exc, (AuthenticationError, BadRequestError)):
        return False
    return False


def _run_provider_operation_with_retries(operation_name: str, operation):
    last_exc: Exception | None = None

    for attempt in range(1, PROVIDER_MAX_ATTEMPTS + 1):
        try:
            return operation()
        except HTTPException:
            raise
        except Exception as exc:
            last_exc = exc
            should_retry = _is_retryable_provider_error(exc) and attempt < PROVIDER_MAX_ATTEMPTS
            if not should_retry:
                if _is_retryable_provider_error(exc):
                    raise RuntimeError(
                        f"{operation_name} failed after {PROVIDER_MAX_ATTEMPTS} attempts: {exc}"
                    ) from exc
                raise
            time.sleep(PROVIDER_RETRY_DELAY_SECONDS * attempt)

    raise RuntimeError(f"{operation_name} failed: {last_exc}") from last_exc


def test_provider_connection(settings: SettingsPayload) -> str:
    validated = _validate_connection_test_settings(settings)
    client = _build_provider_client(validated)

    try:
        client.chat.completions.create(
            model=validated.llm_model.strip(),
            temperature=0,
            max_tokens=1,
            messages=[
                {"role": "system", "content": "Reply with OK."},
                {"role": "user", "content": "Connection test."},
            ],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider connection test failed: {exc}",
        ) from exc

    provider_name = validated.llm_provider_name.strip() or "Provider"
    return f"{provider_name} connection successful."


def _extract_json_object(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Provider did not return valid JSON.") from None
        return json.loads(content[start : end + 1])


def analyze_article_with_provider(session: Session, article: Article, source: Source | None) -> dict:
    client, settings = get_provider_client(session)

    prompt = f"""
You are helping organize a guided reading curriculum.
Return JSON only with these keys:
- tags: string[]
- difficulty: "beginner" | "intermediate" | "advanced"
- stage: "foundation" | "core" | "frontier" | "update"
- estimated_minutes: integer
- one_sentence_summary: string
- checkpoint_questions: string[]
- core_score: number between 0 and 1
- core_reason: string

Article title: {article.title}
Source name: {source.name if source else article.source_name_snapshot or "Unknown"}
Excerpt: {article.content_excerpt or article.raw_summary or ""}

Guidance:
- foundation: introductory, overview, prerequisites
- core: central or must-read content for the topic
- frontier: advanced, specialized, or cutting-edge
- update: release notes, updates, recent changes
- tags should be short normalized phrases
- estimated_minutes should be realistic
- core_score reflects how central this article is for a guided reading track
""".strip()

    def run_completion() -> dict:
        completion = client.chat.completions.create(
            model=settings.llm_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": "You are a precise JSON generator."},
                {"role": "user", "content": prompt},
            ],
        )

        content = completion.choices[0].message.content or "{}"
        return _extract_json_object(content)

    result = _run_provider_operation_with_retries("Article analysis", run_completion)

    tags = [str(tag).strip() for tag in result.get("tags", []) if str(tag).strip()]
    checkpoint_questions = [
        str(question).strip()
        for question in result.get("checkpoint_questions", [])
        if str(question).strip()
    ]

    return {
        "tags": tags[:8],
        "difficulty": result.get("difficulty"),
        "stage": result.get("stage"),
        "estimated_minutes": int(result.get("estimated_minutes") or 10),
        "one_sentence_summary": str(result.get("one_sentence_summary") or "").strip(),
        "checkpoint_questions": checkpoint_questions[:5],
        "core_score": float(result.get("core_score") or 0),
        "core_reason": str(result.get("core_reason") or "").strip(),
    }


def parse_article_candidates_with_provider(
    session: Session, raw_text: str
) -> list[ArticleImportCandidate]:
    client, settings = get_provider_client(session)

    prompt = f"""
You are converting a user-provided article list into structured JSON.
Return JSON only with one key:
- items: array of objects with keys title, url, author, published_at, raw_summary

Rules:
- Include only real articles with a valid HTTP/HTTPS URL.
- Keep title concise and faithful to the source text.
- If a field is missing, return null for it.
- published_at must be ISO 8601 when present.
- Do not invent URLs.

Raw text:
{raw_text}
""".strip()

    def run_completion() -> dict:
        completion = client.chat.completions.create(
            model=settings.llm_model,
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a precise JSON generator."},
                {"role": "user", "content": prompt},
            ],
        )
        content = completion.choices[0].message.content or "{}"
        return _extract_json_object(content)

    result = _run_provider_operation_with_retries("Article list parsing", run_completion)
    items = result.get("items", [])

    candidates: list[ArticleImportCandidate] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        if not title or not url:
            continue
        published_at = None
        published_value = item.get("published_at")
        if isinstance(published_value, str) and published_value.strip():
            normalized = published_value.strip().replace("Z", "+00:00")
            try:
                published_at = datetime.fromisoformat(normalized)
            except ValueError:
                published_at = None

        raw_summary = str(item.get("raw_summary") or "").strip() or None
        candidates.append(
            ArticleImportCandidate(
                title=title[:300],
                url=url[:800],
                author=str(item.get("author") or "").strip() or None,
                published_at=published_at,
                raw_summary=raw_summary[:2000] if raw_summary else None,
                content_excerpt=raw_summary[:2000] if raw_summary else None,
                source_name_snapshot=None,
            )
        )

    return candidates


def generate_weekly_review_with_provider(
    session: Session,
    *,
    week_start: date,
    primary_titles: list[str],
    supplemental_titles: list[str],
    review_theme: str,
) -> dict:
    client, settings = get_provider_client(session)

    prompt = f"""
You are drafting a weekly guided reading plan.
Return JSON only with:
- generated_plan: string
- generated_review: string

Week start: {week_start.isoformat()}
Primary reading candidates: {primary_titles}
Supplemental reading candidates: {supplemental_titles}
Review theme: {review_theme}

Requirements:
- generated_plan should explain what to read this week and why
- generated_review should contain review prompts and next-step guidance
""".strip()

    def run_completion() -> dict:
        completion = client.chat.completions.create(
            model=settings.llm_model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": "You are a precise JSON generator."},
                {"role": "user", "content": prompt},
            ],
        )

        content = completion.choices[0].message.content or "{}"
        return _extract_json_object(content)

    result = _run_provider_operation_with_retries("Weekly review generation", run_completion)

    return {
        "generated_plan": str(result.get("generated_plan") or "").strip(),
        "generated_review": str(result.get("generated_review") or "").strip(),
    }


def plan_weekly_curriculum_with_provider(
    session: Session,
    *,
    week_start: date,
    candidates: list[dict],
) -> dict:
    client, settings = get_provider_client(session)
    serialized_candidates = json.dumps(candidates, ensure_ascii=False)

    prompt = f"""
You are sequencing one week of a guided reading curriculum.
Return JSON only with:
- primary_topic_key: string
- supplemental_topic_key: string | null
- items: array of objects with keys article_id, topic_key, track_type, sequence_rank, reason
- generated_plan: string
- generated_review: string

Week start: {week_start.isoformat()}
Candidates:
{serialized_candidates}

Rules:
- Use only candidate article_id values that appear above.
- Choose exactly one primary topic line and at most one supplemental line.
- Primary line should usually contain 3 to 5 articles.
- Supplemental line should usually contain 1 to 3 articles.
- track_type must be one of "primary", "supplemental", or "skip".
- Keep series articles in order when series_index is present.
- Prefer a pedagogical order inside one line: foundation -> core -> frontier -> update.
- Update articles should only be included if tightly related to the primary line, and they should usually be supplemental.
- Every selected article needs a short reason.
- generated_plan should explain this week's reading sequence.
- generated_review should include review prompts and a suggested next step.
""".strip()

    def run_completion() -> dict:
        completion = client.chat.completions.create(
            model=settings.llm_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": "You are a precise JSON generator."},
                {"role": "user", "content": prompt},
            ],
        )

        content = completion.choices[0].message.content or "{}"
        return _extract_json_object(content)

    result = _run_provider_operation_with_retries("Weekly curriculum planning", run_completion)

    raw_items = result.get("items", [])
    normalized_items: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        article_id = item.get("article_id")
        sequence_rank = item.get("sequence_rank")
        track_type = str(item.get("track_type") or "").strip().lower()
        if not isinstance(article_id, int) or track_type not in {"primary", "supplemental", "skip"}:
            continue
        try:
            rank_value = int(sequence_rank)
        except (TypeError, ValueError):
            rank_value = 999

        normalized_items.append(
            {
                "article_id": article_id,
                "topic_key": str(item.get("topic_key") or "").strip() or None,
                "track_type": track_type,
                "sequence_rank": rank_value,
                "reason": str(item.get("reason") or "").strip(),
            }
        )

    return {
        "primary_topic_key": str(result.get("primary_topic_key") or "").strip() or None,
        "supplemental_topic_key": str(result.get("supplemental_topic_key") or "").strip() or None,
        "items": normalized_items,
        "generated_plan": str(result.get("generated_plan") or "").strip(),
        "generated_review": str(result.get("generated_review") or "").strip(),
    }
