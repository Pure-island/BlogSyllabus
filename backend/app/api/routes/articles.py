from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.db import get_session
from app.models import DifficultyLevel, ReadingStage, ReadingStatus
from app.schemas import (
    ArticleCreate,
    ArticleImportBatchPayload,
    ArticleImportBatchResponse,
    ArticleImportPreviewRequest,
    ArticleImportPreviewResponse,
    ArticleRead,
    ArticleUpdate,
    BatchAnalyzeRequest,
    CurriculumResponse,
    ProgressResponse,
    ReadingLogCreate,
    ReadingLogRead,
    TodayResponse,
)
from app.services.article_service import (
    analyze_article,
    article_to_read,
    create_article,
    create_reading_log,
    get_article_or_404,
    get_curriculum,
    get_progress,
    generate_today,
    list_articles,
    list_reading_logs,
    update_article,
)
from app.services.text_import_service import import_article_candidates, preview_article_import
from app.services.import_service import create_analyze_batch_job

router = APIRouter(tags=["articles"])


@router.get("/articles", response_model=list[ArticleRead])
def read_articles(
    stage: ReadingStage | None = Query(default=None),
    status_value: ReadingStatus | None = Query(default=None, alias="status"),
    difficulty: DifficultyLevel | None = Query(default=None),
    source_id: int | None = Query(default=None),
    is_core: bool | None = Query(default=None),
    tag: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[ArticleRead]:
    return [
        article_to_read(article)
        for article in list_articles(
            session,
            stage=stage,
            status_value=status_value,
            difficulty=difficulty,
            source_id=source_id,
            is_core=is_core,
            tag=tag,
        )
    ]


@router.post("/articles", response_model=ArticleRead, status_code=status.HTTP_201_CREATED)
def create_article_endpoint(payload: ArticleCreate, session: Session = Depends(get_session)) -> ArticleRead:
    return article_to_read(create_article(session, payload))


@router.patch("/articles/{article_id}", response_model=ArticleRead)
def update_article_endpoint(
    article_id: int,
    payload: ArticleUpdate,
    session: Session = Depends(get_session),
) -> ArticleRead:
    article = get_article_or_404(session, article_id)
    return article_to_read(update_article(session, article, payload))


@router.post("/articles/{article_id}/analyze", response_model=ArticleRead)
def analyze_article_endpoint(article_id: int, session: Session = Depends(get_session)) -> ArticleRead:
    article = get_article_or_404(session, article_id)
    return article_to_read(analyze_article(session, article))


@router.post("/articles/analyze-batch")
def analyze_batch_endpoint(
    payload: BatchAnalyzeRequest,
    session: Session = Depends(get_session),
) -> dict[str, int | str]:
    job = create_analyze_batch_job(session, payload.article_ids)
    return {"message": "Analyze batch job created.", "job_id": job.id or 0}


@router.post("/articles/import-preview", response_model=ArticleImportPreviewResponse)
def preview_article_import_endpoint(
    payload: ArticleImportPreviewRequest,
    session: Session = Depends(get_session),
) -> ArticleImportPreviewResponse:
    return preview_article_import(session, payload)


@router.post("/articles/import-batch", response_model=ArticleImportBatchResponse)
def import_article_batch_endpoint(
    payload: ArticleImportBatchPayload,
    session: Session = Depends(get_session),
) -> ArticleImportBatchResponse:
    return import_article_candidates(session, payload)


@router.get("/inbox", response_model=list[ArticleRead])
def read_inbox(
    source_id: int | None = Query(default=None),
    status_value: ReadingStatus | None = Query(default=None, alias="status"),
    difficulty: DifficultyLevel | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[ArticleRead]:
    return [
        article_to_read(article)
        for article in list_articles(
            session,
            status_value=status_value,
            difficulty=difficulty,
            source_id=source_id,
            inbox_only=True,
        )
    ]


@router.get("/curriculum", response_model=CurriculumResponse)
def read_curriculum(session: Session = Depends(get_session)) -> CurriculumResponse:
    return get_curriculum(session)


@router.get("/today", response_model=TodayResponse)
def read_today(session: Session = Depends(get_session)) -> TodayResponse:
    return generate_today(session)


@router.post("/today/generate", response_model=TodayResponse)
def generate_today_endpoint(session: Session = Depends(get_session)) -> TodayResponse:
    return generate_today(session)


@router.get("/progress", response_model=ProgressResponse)
def read_progress(session: Session = Depends(get_session)) -> ProgressResponse:
    return get_progress(session)


@router.get("/reading-logs", response_model=list[ReadingLogRead])
def read_logs(session: Session = Depends(get_session)) -> list[ReadingLogRead]:
    return list_reading_logs(session)


@router.post("/reading-logs", response_model=ReadingLogRead, status_code=status.HTTP_201_CREATED)
def create_log_endpoint(
    payload: ReadingLogCreate,
    session: Session = Depends(get_session),
) -> ReadingLogRead:
    return create_reading_log(session, payload)
