from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.db import get_session
from app.schemas import SourceCheckResponse, SourceCreate, SourceFetchResponse, SourceRead, SourceUpdate
from app.services.import_service import fetch_source_sync
from app.services.source_service import (
    check_source_feed,
    create_source,
    delete_source,
    get_source_or_404,
    list_sources,
    update_source,
)

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceRead])
def read_sources(session: Session = Depends(get_session)) -> list[SourceRead]:
    return [
        SourceRead.model_validate({**source.model_dump(), "article_count": article_count})
        for source, article_count in list_sources(session)
    ]


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source_endpoint(
    payload: SourceCreate, session: Session = Depends(get_session)
) -> SourceRead:
    source = create_source(session, payload)
    return SourceRead.model_validate({**source.model_dump(), "article_count": 0})


@router.get("/{source_id}", response_model=SourceRead)
def read_source(source_id: int, session: Session = Depends(get_session)) -> SourceRead:
    source = get_source_or_404(session, source_id)
    article_count = len(source.articles)
    return SourceRead.model_validate({**source.model_dump(), "article_count": article_count})


@router.patch("/{source_id}", response_model=SourceRead)
def update_source_endpoint(
    source_id: int, payload: SourceUpdate, session: Session = Depends(get_session)
) -> SourceRead:
    source = get_source_or_404(session, source_id)
    updated_source = update_source(session, source, payload)
    article_count = len(updated_source.articles)
    return SourceRead.model_validate({**updated_source.model_dump(), "article_count": article_count})


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source_endpoint(source_id: int, session: Session = Depends(get_session)) -> None:
    source = get_source_or_404(session, source_id)
    delete_source(session, source)


@router.post("/{source_id}/test", response_model=SourceCheckResponse)
def test_source_endpoint(source_id: int, session: Session = Depends(get_session)) -> SourceCheckResponse:
    source = get_source_or_404(session, source_id)
    result = check_source_feed(source)
    return SourceCheckResponse(**result)


@router.post("/{source_id}/fetch", response_model=SourceFetchResponse)
def fetch_source_endpoint(source_id: int, session: Session = Depends(get_session)) -> SourceFetchResponse:
    source = get_source_or_404(session, source_id)
    result = fetch_source_sync(session, source)
    return SourceFetchResponse(message="Feed fetched successfully.", **result)
