from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.db import get_session
from app.schemas import WeeklyReviewRead
from app.services.weekly_service import (
    generate_weekly_review,
    get_current_weekly_review,
    list_weekly_reviews,
)

router = APIRouter(prefix="/weekly", tags=["weekly"])


@router.get("/current", response_model=WeeklyReviewRead | None)
def read_current_weekly_review(session: Session = Depends(get_session)) -> WeeklyReviewRead | None:
    return get_current_weekly_review(session)


@router.post("/generate", response_model=WeeklyReviewRead, status_code=status.HTTP_201_CREATED)
def generate_weekly_review_endpoint(session: Session = Depends(get_session)) -> WeeklyReviewRead:
    return generate_weekly_review(session)


@router.get("/history", response_model=list[WeeklyReviewRead])
def read_weekly_review_history(session: Session = Depends(get_session)) -> list[WeeklyReviewRead]:
    return list_weekly_reviews(session)
