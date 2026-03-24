from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.db import get_session
from app.models import Article, DifficultyLevel, ReadingStage, ReadingStatus, Source
from app.schemas import ArticleCreate, ArticleRead

router = APIRouter(tags=["articles"])


@router.get("/articles", response_model=list[ArticleRead])
def read_articles(session: Session = Depends(get_session)) -> list[Article]:
    return session.exec(select(Article).order_by(Article.created_at.desc())).all()


@router.post("/articles", response_model=ArticleRead, status_code=status.HTTP_201_CREATED)
def create_article(payload: ArticleCreate, session: Session = Depends(get_session)) -> Article:
    existing = session.exec(select(Article).where(Article.url == payload.url)).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An article with this URL already exists.")

    if payload.source_id is not None:
        source = session.get(Source, payload.source_id)
        if source is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found.")

    article = Article.model_validate(payload)
    session.add(article)
    session.commit()
    session.refresh(article)
    return article


@router.get("/inbox", response_model=list[ArticleRead])
def read_inbox(
    source_id: int | None = Query(default=None),
    stage: ReadingStage | None = Query(default=None),
    status_value: ReadingStatus | None = Query(default=None, alias="status"),
    difficulty: DifficultyLevel | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[Article]:
    statement = select(Article).where(Article.stage.is_(None))

    if source_id is not None:
        statement = statement.where(Article.source_id == source_id)
    if stage is not None:
        statement = statement.where(Article.stage == stage)
    if status_value is not None:
        statement = statement.where(Article.status == status_value)
    if difficulty is not None:
        statement = statement.where(Article.difficulty == difficulty)

    return session.exec(statement.order_by(Article.created_at.desc())).all()
