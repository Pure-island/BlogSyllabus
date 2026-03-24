from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.schemas import SettingsPayload
from app.services.settings_service import get_settings_payload, update_settings_payload

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsPayload)
def read_settings(session: Session = Depends(get_session)) -> SettingsPayload:
    return get_settings_payload(session)


@router.put("", response_model=SettingsPayload)
def update_settings(
    payload: SettingsPayload, session: Session = Depends(get_session)
) -> SettingsPayload:
    return update_settings_payload(session, payload)
