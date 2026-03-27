from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.db import get_session
from app.schemas import ImportJobRead, MessageResponse
from app.services.import_service import (
    create_fetch_active_job,
    create_fetch_single_source_job,
    get_import_job_read,
    list_import_jobs,
    retry_import_job,
)

router = APIRouter(prefix="/imports", tags=["imports"])


@router.get("/jobs", response_model=list[ImportJobRead])
def read_import_jobs(session: Session = Depends(get_session)) -> list[ImportJobRead]:
    return list_import_jobs(session)


@router.get("/jobs/{job_id}", response_model=ImportJobRead)
def read_import_job(job_id: int, session: Session = Depends(get_session)) -> ImportJobRead:
    return get_import_job_read(session, job_id)


@router.post("/jobs/{job_id}/retry", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
def retry_import_job_endpoint(job_id: int, session: Session = Depends(get_session)) -> MessageResponse:
    job = retry_import_job(session, job_id)
    return MessageResponse(message=f"Retry scheduled for import job {job.id}.")


@router.post("/sources/fetch-active", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
def fetch_active_sources_endpoint(session: Session = Depends(get_session)) -> MessageResponse:
    job = create_fetch_active_job(session)
    return MessageResponse(message=f"Import job {job.id} created for active sources.")


@router.post("/sources/{source_id}/fetch", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
def fetch_single_source_endpoint(source_id: int, session: Session = Depends(get_session)) -> MessageResponse:
    job = create_fetch_single_source_job(session, source_id)
    return MessageResponse(message=f"Import job {job.id} created for source {source_id}.")
