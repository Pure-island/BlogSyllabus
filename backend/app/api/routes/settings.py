from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.schemas import MessageResponse, SettingsPayload
from app.services.provider_service import test_provider_connection
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


@router.post("/test", response_model=MessageResponse)
def test_settings_provider(payload: SettingsPayload) -> MessageResponse:
    return MessageResponse(message=test_provider_connection(payload))
