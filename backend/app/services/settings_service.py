from sqlmodel import Session, select

from app.models import AppSetting, utc_now
from app.schemas import SettingsPayload

DEFAULT_SETTINGS = {
    "openai_api_key": "",
    "openai_model": "",
    "ui_language": "zh-CN",
    "openai_enabled": "false",
}


def get_settings_payload(session: Session) -> SettingsPayload:
    records = session.exec(select(AppSetting)).all()
    values = {record.key: record.value for record in records}

    merged = {**DEFAULT_SETTINGS, **values}
    return SettingsPayload(
        openai_api_key=merged["openai_api_key"],
        openai_model=merged["openai_model"],
        ui_language=merged["ui_language"] or "zh-CN",
        openai_enabled=str(merged["openai_enabled"]).lower() == "true",
    )


def update_settings_payload(session: Session, payload: SettingsPayload) -> SettingsPayload:
    settings_map = {
        "openai_api_key": payload.openai_api_key,
        "openai_model": payload.openai_model,
        "ui_language": payload.ui_language,
        "openai_enabled": str(payload.openai_enabled).lower(),
    }

    for key, value in settings_map.items():
        setting = session.exec(select(AppSetting).where(AppSetting.key == key)).first()
        if setting is None:
            setting = AppSetting(key=key, value=value)
            session.add(setting)
        else:
            setting.value = value
            setting.updated_at = utc_now()

    session.commit()
    return get_settings_payload(session)
