def test_settings_connection_requires_api_key_and_model(client) -> None:
    response = client.post(
        "/api/settings/test",
        json={
            "llm_provider_name": "OpenAI-compatible",
            "llm_base_url": "https://api.openai.com/v1",
            "llm_api_key": "",
            "llm_model": "",
            "llm_enabled": False,
            "ui_language": "zh-CN",
        },
    )

    assert response.status_code == 400
    assert response.json()["message"] == (
        "Provider API key and model are required for connection testing."
    )


def test_settings_connection_returns_success_message(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.settings.test_provider_connection",
        lambda payload: f"{payload.llm_provider_name} connection successful.",
    )

    response = client.post(
        "/api/settings/test",
        json={
            "llm_provider_name": "OpenAI-compatible",
            "llm_base_url": "https://api.openai.com/v1",
            "llm_api_key": "sk-test",
            "llm_model": "gpt-4.1-mini",
            "llm_enabled": False,
            "ui_language": "zh-CN",
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "OpenAI-compatible connection successful."
