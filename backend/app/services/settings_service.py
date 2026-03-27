from sqlmodel import Session, select

from app.models import AppSetting, utc_now
from app.schemas import SettingsPayload

LEGACY_KEY_MAP = {
    "openai_api_key": "llm_api_key",
    "openai_model": "llm_model",
    "openai_enabled": "llm_enabled",
}

DEFAULT_SETTINGS = {
    "llm_provider_name": "OpenAI-compatible",
    "llm_base_url": "https://api.openai.com/v1",
    "llm_api_key": "",
    "llm_model": "",
    "llm_enabled": "false",
    "ui_language": "zh-CN",
}


def _get_setting_record(session: Session, key: str) -> AppSetting | None:
    return session.exec(select(AppSetting).where(AppSetting.key == key)).first()


def _normalize_raw_settings(values: dict[str, str]) -> dict[str, str]:
    normalized = {**DEFAULT_SETTINGS}
    normalized.update(values)

    for legacy_key, new_key in LEGACY_KEY_MAP.items():
        if values.get(legacy_key) and not values.get(new_key):
            normalized[new_key] = values[legacy_key]

    return normalized


def get_settings_payload(session: Session) -> SettingsPayload:
    records = session.exec(select(AppSetting)).all()
    values = {record.key: record.value for record in records}
    merged = _normalize_raw_settings(values)

    return SettingsPayload(
        llm_provider_name=merged["llm_provider_name"] or "OpenAI-compatible",
        llm_base_url=merged["llm_base_url"],
        llm_api_key=merged["llm_api_key"],
        llm_model=merged["llm_model"],
        llm_enabled=str(merged["llm_enabled"]).lower() == "true",
        ui_language=merged["ui_language"] or "zh-CN",
    )


def update_settings_payload(session: Session, payload: SettingsPayload) -> SettingsPayload:
    settings_map = {
        "llm_provider_name": payload.llm_provider_name,
        "llm_base_url": payload.llm_base_url,
        "llm_api_key": payload.llm_api_key,
        "llm_model": payload.llm_model,
        "llm_enabled": str(payload.llm_enabled).lower(),
        "ui_language": payload.ui_language,
    }

    for legacy_key in LEGACY_KEY_MAP:
        legacy_record = _get_setting_record(session, legacy_key)
        if legacy_record is not None:
            session.delete(legacy_record)

    for key, value in settings_map.items():
        setting = _get_setting_record(session, key)
        if setting is None:
            setting = AppSetting(key=key, value=value)
            session.add(setting)
        else:
            setting.value = value
            setting.updated_at = utc_now()

    session.commit()
    return get_settings_payload(session)
